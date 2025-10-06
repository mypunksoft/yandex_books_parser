import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
from urllib.parse import urlparse
import csv
import os
import json

# Файлы для работы скрипта
PROGRESS_FILE = 'parser_progress.json'
ERROR_URLS_FILE = 'error_urls.txt'
OUTPUT_CSV = 'books_data.csv'

def parse_book_info(url):

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Парсим автора
        author_element = soup.find('a', {'data-test-id': 'CONTENT_AUTHOR_AUTHOR_NAME'})
        author = author_element.text.strip() if author_element else "Автор не найден"
        
        # Парсим название книги
        title_element = soup.find('span', {'data-test-id': 'CONTENT_TITLE_MAIN'})
        title = title_element.text.strip() if title_element else "Название не найдено"
        
        # Очистка названия от лишних пробелов и символов
        title = ' '.join(title.split())
        
        return {
            'url': url,
            'author': author,
            'title': title,
            'status': 'Успешно',
            'has_error': False
        }
        
    except requests.RequestException as e:
        return {
            'url': url,
            'author': '',
            'title': '',
            'status': f'Ошибка запроса: {str(e)}',
            'has_error': True
        }
    except Exception as e:
        return {
            'url': url,
            'author': '',
            'title': '',
            'status': f'Ошибка парсинга: {str(e)}',
            'has_error': True
        }

def parse_sitemap(xml_file):

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Namespace для sitemap
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        for url_elem in root.findall('ns:url', ns):
            loc_elem = url_elem.find('ns:loc', ns)
            if loc_elem is not None:
                urls.append(loc_elem.text)
        
        return urls
    except Exception as e:
        print(f"Ошибка при чтении sitemap: {e}")
        return []

def write_to_csv(book_info, output_file, is_first=False):
    """
    Записывает информацию о книге в CSV файл
    """
    mode = 'w' if is_first else 'a'
    with open(output_file, mode, newline='', encoding='utf-8') as csvfile:
        fieldnames = ['url', 'author', 'title', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if is_first:
            writer.writeheader()
        writer.writerow({
            'url': book_info['url'],
            'author': book_info['author'],
            'title': book_info['title'],
            'status': book_info['status']
        })

def write_error_url(url, error_message):
    """
    Записывает URL с ошибкой в txt файл
    """
    with open(ERROR_URLS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{url} | {error_message}\n")

def save_progress(current_index, total_urls, xml_file):
    """
    Сохраняет прогресс парсинга
    """
    progress_data = {
        'current_index': current_index,
        'total_urls': total_urls,
        'xml_file': xml_file,
        'timestamp': time.time()
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, indent=2)

def load_progress():
    """
    Загружает сохраненный прогресс
    """
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def clear_progress():
    """
    Удаляет файл прогресса
    """
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

def get_error_urls():
    """
    Читает URLs с ошибками из txt файла
    """
    if not os.path.exists(ERROR_URLS_FILE):
        return []
    
    error_urls = []
    with open(ERROR_URLS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                # Извлекаем только URL (до символа |)
                url = line.split('|')[0].strip()
                error_urls.append(url)
    return error_urls

def retry_error_urls():
    """
    Повторно обрабатывает URLs с ошибками
    """
    error_urls = get_error_urls()
    
    if not error_urls:
        print("\n✓ Нет URLs с ошибками для повторной обработки")
        return
    
    print(f"\n{'='*60}")
    print(f"Найдено {len(error_urls)} URLs с ошибками")
    print(f"Начинаем повторную обработку...")
    print(f"{'='*60}\n")
    
    # Создаем временный файл для новых ошибок
    temp_error_file = 'error_urls_temp.txt'
    
    successful = 0
    still_errors = 0
    
    for i, url in enumerate(error_urls):
        print(f"\nПовторная обработка {i + 1}/{len(error_urls)}: {url}")
        
        book_info = parse_book_info(url)
        
        # Записываем результат в CSV
        write_to_csv(book_info, OUTPUT_CSV, is_first=False)
        
        if book_info['has_error']:
            print(f"  ✗ Ошибка: {book_info['status']}")
            with open(temp_error_file, 'a', encoding='utf-8') as f:
                f.write(f"{url} | {book_info['status']}\n")
            still_errors += 1
        else:
            print(f"  ✓ Успешно!")
            print(f"  ✓ Автор: {book_info['author']}")
            print(f"  ✓ Название: {book_info['title']}")
            successful += 1
        
        time.sleep(1)
    
    # Заменяем старый файл ошибок новым
    if os.path.exists(ERROR_URLS_FILE):
        os.remove(ERROR_URLS_FILE)
    if os.path.exists(temp_error_file):
        os.rename(temp_error_file, ERROR_URLS_FILE)
    
    print(f"\n{'='*60}")
    print(f"Повторная обработка завершена!")
    print(f"Успешно обработано: {successful}/{len(error_urls)}")
    print(f"Всё ещё с ошибками: {still_errors}/{len(error_urls)}")
    print(f"{'='*60}\n")

def main():
    print(f"\n{'='*60}")
    print("Парсер Яндекс.Книги")
    print(f"{'='*60}\n")
    
    # Проверяем наличие сохраненного прогресса
    progress = load_progress()
    
    if progress:
        print(f"Найден сохраненный прогресс:")
        print(f"  Файл: {progress['xml_file']}")
        print(f"  Обработано: {progress['current_index']}/{progress['total_urls']} URLs")
        
        choice = input("\nПродолжить с сохраненного места? (y/n): ").strip().lower()
        
        if choice == 'y':
            xml_file = progress['xml_file']
            start_position = progress['current_index'] + 1
            
            # Проверяем существование файла
            if not os.path.exists(xml_file):
                print(f"Ошибка: Файл '{xml_file}' не найден")
                clear_progress()
                return
            
            urls = parse_sitemap(xml_file)
            if not urls:
                print("Не удалось найти URLs в sitemap")
                return
        else:
            clear_progress()
            progress = None
    
    if not progress:
        # Начинаем с начала
        xml_file = input("Введите путь к XML файлу (или Enter для 'sitemap-books.xml'): ").strip()
        if xml_file == "":
            xml_file = 'sitemap-books.xml'
        
        if not os.path.exists(xml_file):
            print(f"Ошибка: Файл '{xml_file}' не найден")
            return
        
        print("\nЧтение sitemap...")
        urls = parse_sitemap(xml_file)
        
        if not urls:
            print("Не удалось найти URLs в sitemap")
            return
        
        print(f"Найдено {len(urls)} URLs")
        
        # Спрашиваем начальную позицию
        while True:
            try:
                position = input("\nВведите номер URL, с которого начать (или Enter для начала с 1): ").strip()
                if position == "":
                    start_position = 1
                    break
                position = int(position)
                if position < 1:
                    print("Номер должен быть больше 0")
                    continue
                if position > len(urls):
                    print(f"Ошибка: Начальная позиция ({position}) больше количества URLs ({len(urls)})")
                    continue
                start_position = position
                break
            except ValueError:
                print("Пожалуйста, введите корректное число")
        
        # Очищаем файл ошибок при новом запуске
        if os.path.exists(ERROR_URLS_FILE):
            os.remove(ERROR_URLS_FILE)
    
    # Счетчики для статистики
    successful = 0
    errors = 0
    
    print(f"\n{'='*60}")
    print(f"Начинаем парсинг с позиции {start_position}/{len(urls)}")
    print(f"{'='*60}\n")
    
    # Парсим информацию о книгах
    try:
        for i in range(start_position - 1, len(urls)):
            url = urls[i]
            print(f"\nОбрабатывается {i + 1}/{len(urls)}: {url}")
            
            book_info = parse_book_info(url)
            
            # Записываем результат в CSV
            is_first = (i == start_position - 1) and not os.path.exists(OUTPUT_CSV)
            write_to_csv(book_info, OUTPUT_CSV, is_first=is_first)
            
            # Если ошибка - записываем в txt
            if book_info['has_error']:
                write_error_url(url, book_info['status'])
                print(f"  ✗ Ошибка: {book_info['status']}")
                errors += 1
            else:
                print(f"  ✓ Автор: {book_info['author']}")
                print(f"  ✓ Название: {book_info['title']}")
                successful += 1
            
            # Статистика в реальном времени
            total_processed = i - start_position + 2
            print(f"  Прогресс: {total_processed}/{len(urls) - start_position + 1} | Успешно: {successful} | Ошибок: {errors}")
            
            # Сохраняем прогресс каждые 10 итераций
            if (i + 1) % 10 == 0:
                save_progress(i + 1, len(urls), xml_file)
            
            time.sleep(1)
        
        # Основной парсинг завершен
        clear_progress()
        
        print(f"\n{'='*60}")
        print(f"Основной парсинг завершен!")
        print(f"Результаты сохранены в {OUTPUT_CSV}")
        print(f"\nИтоговая статистика:")
        print(f"Успешно обработано: {successful}/{len(urls) - start_position + 1}")
        print(f"С ошибками: {errors}/{len(urls) - start_position + 1}")
        
        if errors > 0:
            print(f"\nСсылки с ошибками сохранены в {ERROR_URLS_FILE}")
        
        print(f"{'='*60}")
        
        # Предлагаем повторно обработать ошибки
        if errors > 0:
            choice = input("\nПопробовать повторно обработать URLs с ошибками? (y/n): ").strip().lower()
            if choice == 'y':
                retry_error_urls()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Парсинг прерван пользователем")
        save_progress(i, len(urls), xml_file)
        print(f"Прогресс сохранен. Обработано {i + 1}/{len(urls)} URLs")
        print("Запустите скрипт снова, чтобы продолжить с этого места")
    except Exception as e:
        print(f"\n\n⚠ Произошла ошибка: {e}")
        save_progress(i, len(urls), xml_file)
        print(f"Прогресс сохранен. Обработано {i + 1}/{len(urls)} URLs")

if __name__ == "__main__":
    main()