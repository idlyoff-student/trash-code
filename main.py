import logging
import pymysql
from lxml import html
import telebot

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Замените 'YOUR_TELEGRAM_BOT_TOKEN' на токен вашего бота
BOT_TOKEN = "7873490515:AAGj7FedhQvNRBrHs_2R1do5cNJ7UvNsatw"

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

def extract_element_string(html_string: str) -> str:
    """Извлекает текст из HTML-строки, используя lxml."""
    if not html_string:
        return None
    node = html.fromstring(html_string)
    return "".join(node.itertext())

def get_questions_and_answers(cmid: str) -> str:
    """Получает вопросы и ответы из базы данных moodle_kkt."""
    try:
        connection = pymysql.connect(
            host="kktbel.ru",
            port=44970,
            user="kktbel_ro_user",
            password="UEPr%SDpgAVD",
            database="moodle_kkt",
            cursorclass=pymysql.cursors.DictCursor # Использовать DictCursor для удобства доступа к данным
        )

        with connection.cursor() as cursor:
            # Получаем instance из mdl_course_modules
            cursor.execute("SELECT instance FROM mdl_course_modules WHERE id = %s;", (cmid,))
            result = cursor.fetchone()

            if not result:
                return "CMID не найден."

            _id: int = result['instance']

            # Получаем questionid из mdl_quiz_slots
            cursor.execute("SELECT questionid FROM mdl_quiz_slots WHERE quizid = %s;", (_id,))
            questions = cursor.fetchall()

            if not questions:
                return "Вопросы не найдены для данного CMID."

            result_list = []
            counter: int = 1

            for question_data in questions:
                question_id: int = question_data['questionid']

                # Получаем questiontext из mdl_question
                cursor.execute("SELECT questiontext FROM mdl_question WHERE id = %s;", (question_id,))
                question_text_result = cursor.fetchone()

                if not question_text_result:
                    continue

                question_name: str = extract_element_string(question_text_result['questiontext'])

                if question_name is None:
                    continue

                # Получаем answer и fraction из mdl_question_answers
                cursor.execute("SELECT answer, fraction FROM mdl_question_answers WHERE question = %s;", (question_id,))
                variants = cursor.fetchall()

                if not variants:
                    continue  # Нет вариантов ответа

                awaited_variant: dict = {"answer": "", "fraction": 0}

                for variant in variants:
                    fraction: float = variant['fraction']
                    if fraction > awaited_variant["fraction"]:
                        awaited_variant = {"answer": variant['answer'], "fraction": fraction}

                answer: str = extract_element_string(awaited_variant["answer"])
                result_list.append(f"{counter}. {question_name} // {answer}")
                counter += 1

        connection.close()
        return "\n".join(result_list) if result_list else "Вопросы не найдены."

    except pymysql.MySQLError as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        return "Произошла ошибка при подключении к базе данных."
    except Exception as e:
        logger.exception(f"Необработанная ошибка: {e}")
        return "Произошла непредвиденная ошибка."


@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start."""
    bot.reply_to(message, "Привет! Введите CMID для получения вопросов и ответов.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех текстовых сообщений (кроме команд)."""
    cmid = message.text
    response = get_questions_and_answers(cmid)
    bot.reply_to(message, response)


def main():
    """Запускает бота."""
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.exception(f"Бот упал с ошибкой: {e}")


if __name__ == '__main__':
    main()
