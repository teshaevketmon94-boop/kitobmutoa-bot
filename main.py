
import os
import glob
import json
import time
import requests
import fitz

TOKEN = os.getenv("KITOB_BOT_TOKEN")
CHAT_ID = os.getenv("KITOB_CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PROGRESS_FILE = "progress.json"



def find_pdf():
    files = glob.glob("*.pdf")

    if len(files) == 0:
        raise FileNotFoundError("PDF китоб топилмади")

    if len(files) > 1:
        raise ValueError("Репозиторийда бир нечта PDF бор")

    return files[0]


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return 0

    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("next_page", 0)


def save_progress(next_page):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"next_page": next_page},
            f
        )


def translate_to_uzbek(text):
    url = "https://api.groq.com/openai/v1/chat/completions"

    prompt = f"""
Сен рус тилидан ўзбек тилига таржима қилувчи
диний матнлар мутахассисисан.

Қуйидаги русча китоб матнини ўзбек тилига
кирилл ёзувида тўлиқ ва аниқ таржима қил.

Талаблар:
1. Бирор жумлани ташлаб кетма.
2. Матнни қисқартирма ва ўзингдан изоҳ қўшма.
3. Ақидавий ва ҳадисий атамаларни эҳтиёткорлик билан таржима қил.
4. Арабча оятлар, ҳадислар ва манбаларни асл ҳолича сақла.
5. Муаллифнинг фикри ва услубини сақла.
6. Фақат ўзбекча таржимани қайтар.

Русча асл матн:

{text}
"""

    for attempt in range(4):
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openai/gpt-oss-20b",
"reasoning_effort": "low",
"include_reasoning": False,
"max_completion_tokens": 8192,
"messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.2
                },
                timeout=300,
            )
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError):
            time.sleep(15 * (attempt + 1))
            continue

        if response.status_code in (429, 500, 502, 503):
            time.sleep(10 * (attempt + 1))
            continue

        response.raise_for_status()
        data = response.json()

        result = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not result:
            print("Groq жавоби:", data)
            raise ValueError("Groq таржима матнини қайтармади")

        return result

    raise RuntimeError("Groq API бир неча марта хатолик берди")


def split_message(text, limit=3900):
    chunks = []

    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)

        if cut < 1:
            cut = limit

        chunks.append(text[:cut])
        text = text[cut:].lstrip()

    if text:
        chunks.append(text)

    return chunks


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    for chunk in split_message(text):
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": chunk,
            },
            timeout=60,
        )

        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram хатоси: {result}")

        time.sleep(1)


def main():
    if not TOKEN or not CHAT_ID or not GROQ_API_KEY:
        raise ValueError("Керакли API калитлар топилмади")

    pdf_file = find_pdf()
    next_page = load_progress()

    with fitz.open(pdf_file) as pdf:
        total_pages = len(pdf)

        if next_page >= total_pages:
            print("Китобнинг барча саҳифалари юборилган.")
            return

        end_page = min(next_page + 10, total_pages)

        for index in range(next_page, end_page):
            page = pdf[index]
            russian_text = page.get_text("text").strip()

            if not russian_text:
                raise ValueError(
                    f"{index + 1}-саҳифадан матн олинмади. "
                    "Саҳифа ташлаб кетилмади."
                )

            uzbek_text = translate_to_uzbek(russian_text)

            message = (
                "📖 Китоб: ар-Радд ‘аля-ль-джахмия\n"
                f"📄 Саҳифа: {index + 1}\n\n"
                "🇷🇺 Русча асл матн:\n"
                f"{russian_text}\n\n"
                "🇺🇿 Ўзбекча таржима:\n"
                f"{uzbek_text}"
            )

            send_message(message)

            save_progress(index + 1)

            print(f"{index + 1}-саҳифа юборилди.")

    print("Бугунги 10 саҳифа юбориш тугалланди.")


if __name__ == "__main__":
    main()
        
