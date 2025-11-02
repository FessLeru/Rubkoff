import requests
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://rubkoff.ru"


def get_soup(url):
    """Загружает страницу и возвращает объект BeautifulSoup"""
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def get_project_links():
    """Находит все ссылки на проекты"""
    print("🔍 Загружаю список проектов...")
    soup = get_soup(f"{BASE_URL}/nashi-raboty/")
    links = []
    for a in soup.select("a.product-card, a.project-card"):
        href = a.get("href")
        if href and href.startswith("/nashi-raboty/") and href not in links:
            links.append(BASE_URL + href)
    print(f"📂 Найдено {len(links)} проектов.")
    return links


def parse_project(url):
    """Парсит данные одного проекта"""
    print(f"📸 Обрабатываю: {url}")
    soup = get_soup(url)

    # Удаляем блок "Похожие проекты"
    for bad in soup.find_all(
        lambda tag: tag.name == "section" and (
            "similar" in " ".join(tag.get("class", [])) or
            "related" in " ".join(tag.get("class", [])) or
            "Похожие проекты" in tag.get_text()
        )
    ):
        bad.decompose()

    # Название
    title = soup.select_one("h1")
    title = title.get_text(strip=True) if title else "Без названия"

    # Фото из основного слайдера
    images = []
    gallery = soup.select_one(".product-gallery, .swiper, .product-photos, .project-gallery")
    if gallery:
        for img in gallery.select("img"):
            src = img.get("data-src") or img.get("src")
            if src and "upload" in src:
                if not src.startswith("http"):
                    src = BASE_URL + src
                if src not in images:
                    images.append(src)

    # --- НОВОЕ: Описание из блока .project-desc-text ---
    desc_block = soup.select_one(".project-desc-text")
    description = ""
    if desc_block:
        for el in desc_block.find_all(["h4", "p"]):
            text = el.get_text(" ", strip=True)
            if text and text.lower() != "о проекте":
                description += text + "\n"

    # --- НОВОЕ: Таблица характеристик .desc-table__chars ---
    characteristics = {}
    table = soup.select_one("table.desc-table__chars")
    if table:
        for tr in table.select("tr"):
            tds = tr.select("td")
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                if key:
                    characteristics[key] = val

    return {
        "url": url,
        "title": title,
        "description": description.strip(),
        "characteristics": characteristics,
        "images": images
    }


def main():
    projects_data = []
    links = get_project_links()

    for i, link in enumerate(links, start=1):
        try:
            print(f"[{i}/{len(links)}]")
            data = parse_project(link)
            projects_data.append(data)
            time.sleep(1)
        except Exception as e:
            print(f"❌ Ошибка при обработке {link}: {e}")

    with open("rubkoff_projects.json", "w", encoding="utf-8") as f:
        json.dump(projects_data, f, ensure_ascii=False, indent=2)

    print("\n✅ Готово! Сохранено в rubkoff_projects.json")


if __name__ == "__main__":
    main()
