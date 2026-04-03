import csv
import json
import time
import requests
from datetime import datetime, timezone

USER_AGENT = "VacancyAnalyticsApp/1.0 (tulaeva03@mail.ru)"

API_BASE_URL = "https://api.hh.ru"
VACANCIES_SEARCH_URL = f"{API_BASE_URL}/vacancies"
VACANCY_DETAIL_URL = f"{API_BASE_URL}/vacancies/{{id}}"

# Параметры, чтобы нас не забанили
REQUEST_DELAY = 1.5  # Задержка 1.5 сек
OUTPUT_JSON = "hh_business_analyst_vacancies.json"
OUTPUT_CSV = "hh_business_analyst_vacancies.csv"

# Списки запросов
SEARCH_QUERIES = [
    "бизнес-аналитик", "бизнес аналитик", "аналитик бизнес-процессов", 
    "business analyst", "it business analyst", "аналитик требований"
]

def get_data(url, params=None):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        # Если пришла ошибка 403, значит нас всё еще блокируют
        if response.status_code == 403:
            print("!!! Ошибка 403: Нас заблокировали. Попробуй сменить User-Agent или подождать.")
            return None
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при запросе к {url}: {e}")
        return None

def main():
    all_vacancies = []
    seen_ids = set()

    print(f"Начинаем сбор данных... (Задержка между запросами: {REQUEST_DELAY} сек)")

    for query in SEARCH_QUERIES:
        print(f"--- Ищем: {query} ---")
        # Собираем только первые 20 страниц (2000 вакансий), чтобы не уйти в бесконечность
        for page in range(20): 
            params = {
                "text": query,
                "area": 113, # Вся Россия
                "per_page": 100,
                "page": page
            }
            
            search_results = get_data(VACANCIES_SEARCH_URL, params)
            if not search_results or not search_results.get("items"):
                break

            for item in search_results["items"]:
                v_id = item["id"]
                if v_id in seen_ids: continue
                seen_ids.add(v_id)

                # Получаем подробности каждой вакансии
                print(f"Загружаем детали вакансии ID: {v_id}")
                details = get_data(VACANCY_DETAIL_URL.format(id=v_id))
                
                if details:
                    # Собираем нужные поля для дашборда (БЕЗ описания, но С графиком и ссылкой)
                    vacancy_info = {
                        "id": v_id,
                        "name": details.get("name"),
                        "company": details.get("employer", {}).get("name"),
                        "city": details.get("area", {}).get("name"),
                        "experience": details.get("experience", {}).get("name"),
                        "schedule": details.get("schedule", {}).get("name"),
                        "employment": details.get("employment", {}).get("name"),
                        "key_skills": [s.get("name") for s in details.get("key_skills", [])],
                        "salary_from": (details.get("salary") or {}).get("from"),
                        "salary_to": (details.get("salary") or {}).get("to"),
                        "currency": (details.get("salary") or {}).get("currency"),
                        "published_at": details.get("published_at"),
                        "alternate_url": details.get("alternate_url")
                    }
                    all_vacancies.append(vacancy_info)
                
                time.sleep(REQUEST_DELAY) # Пауза, чтобы не забанили

            if page >= search_results.get("pages", 0) - 1:
                break

    # Сохраняем в JSON (для будущего дашборда)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_vacancies, f, ensure_ascii=False, indent=4)
    
    # Сохраняем в CSV (для Excel)
    if all_vacancies:
        with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_vacancies[0].keys(), delimiter=";")
            writer.writeheader()
            writer.writerows(all_vacancies)

    print(f"Готово! Собрано {len(all_vacancies)} вакансий.")

if __name__ == "__main__":
    main()