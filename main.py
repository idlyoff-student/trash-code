import logging
from pymysql import Connection, connect
from lxml import html
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_element_string(html_string: str) -> str:
    if html_string == "":
        return None
    node = html.fromstring(html_string)
    return "".join(node.itertext())

def get_questions_and_answers(cmid: str) -> str:
    connection: Connection = connect(
        host="kktbel.ru",
        port=44970,
        user="kktbel_ro_user",
        password="UEPr%SDpgAVD",
        database="moodle_kkt"
    )

    result = []
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT instance FROM mdl_course_modules WHERE id = {cmid};")
        _id: int = cursor.fetchone()
        if not _id:
            return "CMID не найден."

        _id = _id[0]
        cursor.execute(f"SELECT questionid FROM mdl_quiz_slots WHERE quizid = {_id};")
        counter: int = 1

        for question in cursor.fetchall():
            question: int = question[0]
            cursor.execute(f"SELECT questiontext FROM mdl_question WHERE id = {question}")
            question_name: str = extract_element_string(cursor.fetchone()[0])

            if question_name is None:
                continue

            cursor.execute(f"SELECT answer, fraction FROM mdl_question_answers WHERE question = {question}")
            awaited_variant: dict = {"answer": "", "fraction": 0}

            for variant in cursor.fetchall():
                fraction: float = variant[1]
                if fraction > awaited_variant["fraction"]:
                    awaited_variant = {"answer": variant[0], "fraction": fraction}

            answer: str = extract_element_string(awaited_variant["answer"])
            result.append(f"{counter}. {question_name} // {answer}")
            counter += 1

    connection.close()
    return "\n".join(result) if result else "Вопросы не найдены."

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Введите CMID для получения вопросов и ответов.')

def handle_message(update: Update, context: CallbackContext) -> None:
    cmid = update.message.text
    response = get_questions_and_answers(cmid)
    update.message.reply_text(response)

def main() -> None:
    updater = Updater("7873490515:AAGj7FedhQvNRBrHs_2R1do5cNJ7UvNsatw")

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
