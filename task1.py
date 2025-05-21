from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Настройки бота
API_TOKEN = 'ВАШ_TELEGRAM_BOT_TOKEN'
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Данные меню (можно заменить на базу данных)
menu = {
    "Пицца": {
        "Маргарита": 450,
        "Пепперони": 550,
        "4 Сыра": 600,
    },
    "Бургеры": {
        "Чизбургер": 250,
        "Гамбургер": 200,
        "Биг Мак": 350,
    },
    "Напитки": {
        "Кола": 100,
        "Фанта": 100,
        "Вода": 80,
    }
}

# Состояния для заказа
class OrderStates(StatesGroup):
    WAITING_CATEGORY = State()
    WAITING_ITEM = State()
    WAITING_ADDRESS = State()
    WAITING_PAYMENT = State()

# Корзина пользователя (временное хранилище)
user_cart = {}

# Клавиатура главного меню
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🍕 Пицца"), KeyboardButton("🍔 Бургеры"))
    keyboard.add(KeyboardButton("🥤 Напитки"), KeyboardButton("🛒 Корзина"))
    keyboard.add(KeyboardButton("📦 Оформить заказ"))
    return keyboard

# Старт бота
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "🍕 Добро пожаловать в бот доставки еды!\n"
        "Выберите категорию:",
        reply_markup=main_menu()
    )

# Вывод меню
@dp.message_handler(lambda msg: msg.text in ["🍕 Пицца", "🍔 Бургеры", "🥤 Напитки"])
async def show_category(message: types.Message):
    category = message.text.replace("🍕 ", "").replace("🍔 ", "").replace("🥤 ", "")
    items = menu.get(category, {})
    
    keyboard = InlineKeyboardMarkup()
    for item, price in items.items():
        keyboard.add(InlineKeyboardButton(f"{item} - {price}₽", callback_data=f"item_{category}_{item}"))
    
    await message.answer(f"Меню {category}:", reply_markup=keyboard)

# Добавление в корзину
@dp.callback_query_handler(lambda call: call.data.startswith("item_"))
async def add_to_cart(call: types.CallbackQuery):
    _, category, item = call.data.split("_")
    price = menu[category][item]
    
    user_id = call.from_user.id
    if user_id not in user_cart:
        user_cart[user_id] = []
    
    user_cart[user_id].append({"item": item, "price": price, "category": category})
    await call.answer(f"✅ {item} добавлен в корзину!")

# Просмотр корзины
@dp.message_handler(lambda msg: msg.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_cart or not user_cart[user_id]:
        await message.answer("🛒 Корзина пуста!")
        return
    
    cart_text = "🛒 Ваш заказ:\n"
    total = 0
    for item in user_cart[user_id]:
        cart_text += f"- {item['item']} ({item['price']}₽)\n"
        total += item['price']
    
    cart_text += f"\n💳 Итого: {total}₽"
    await message.answer(cart_text)

# Оформление заказа
@dp.message_handler(lambda msg: msg.text == "📦 Оформить заказ")
async def start_order(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_cart or not user_cart[user_id]:
        await message.answer("❌ Корзина пуста!")
        return
    
    await message.answer("📝 Введите ваш адрес доставки:")
    await OrderStates.WAITING_ADDRESS.set()

# Получение адреса и выбор оплаты
@dp.message_handler(state=OrderStates.WAITING_ADDRESS)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text
    await state.update_data(address=address)
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💳 Онлайн"), KeyboardButton("💰 Наличными"))
    
    await message.answer("💵 Выберите способ оплаты:", reply_markup=keyboard)
    await OrderStates.WAITING_PAYMENT.set()

# Подтверждение заказа
@dp.message_handler(state=OrderStates.WAITING_PAYMENT)
async def process_payment(message: types.Message, state: FSMContext):
    payment_method = message.text
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    data = await state.get_data()
    address = data.get("address", "Не указан")
    
    # Формируем заказ
    total = sum(item['price'] for item in user_cart[user_id])
    order_text = (
        "✅ Заказ оформлен!\n"
        f"📍 Адрес: {address}\n"
        f"💳 Способ оплаты: {payment_method}\n"
        f"🍕 Состав заказа:\n"
    )
    
    for item in user_cart[user_id]:
        order_text += f"- {item['item']} ({item['price']}₽)\n"
    
    order_text += f"\n💸 Итого: {total}₽\n\n🚀 Доставка в течение 60 минут!"
    
    await message.answer(order_text, reply_markup=main_menu())
    
    # Оповещение администратора (можно заменить на реальный чат)
    admin_chat_id = "ВАШ_CHAT_ID"
    await bot.send_message(admin_chat_id, f"📦 Новый заказ!\n{order_text}")
    
    # Очистка корзины
    user_cart[user_id] = []
    await state.finish()

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)