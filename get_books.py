import argparse
from datetime import datetime
import json
import os
import re
import time

from urllib.request import urlopen
from urllib.request import HTTPError
import bs4


def get_all_lists(soup):

    lists = []
    list_count_dict = {}

    if soup.find('a', text='More lists with this book...'):

        lists_url = soup.find('a', text='More lists with this book...')['href']

        source = urlopen('https://www.goodreads.com' + lists_url)
        soup = bs4.BeautifulSoup(source, 'lxml')
        lists += [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'cell'})]

        i = 0
        while soup.find('a', {'class': 'next_page'}) and i <= 10:

            time.sleep(2)
            next_url = 'https://www.goodreads.com' + soup.find('a', {'class': 'next_page'})['href']
            source = urlopen(next_url)
            soup = bs4.BeautifulSoup(source, 'lxml')

            lists += [node.text for node in soup.find_all('div', {'class': 'cell'})]
            i += 1

        # Format lists text.
        for _list in lists:
            # _list_name = ' '.join(_list.split()[:-8])
            # _list_rank = int(_list.split()[-8][:-2]) 
            # _num_books_on_list = int(_list.split()[-5].replace(',', ''))
            # list_count_dict[_list_name] = _list_rank / float(_num_books_on_list)     # TODO: switch this back to raw counts
            _list_name = _list.split()[:-2][0]
            _list_count = int(_list.split()[-2].replace(',', ''))
            list_count_dict[_list_name] = _list_count

    return list_count_dict


def get_shelves(soup):

    shelf_count_dict = {}
    
    if soup.find('a', text='See top shelves…'):

        # Find shelves text.
        shelves_url = soup.find('a', text='See top shelves…')['href']
        source = urlopen('https://www.goodreads.com' + shelves_url)
        soup = bs4.BeautifulSoup(source, 'lxml')
        shelves = [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'shelfStat'})]
        
        # Format shelves text.
        shelf_count_dict = {}
        for _shelf in shelves:
            _shelf_name = _shelf.split()[:-2][0]
            _shelf_count = int(_shelf.split()[-2].replace(',', ''))
            shelf_count_dict[_shelf_name] = _shelf_count

    return shelf_count_dict


def get_genres(soup):
    genres = []
    for node in soup.find_all('div', {'class': 'left'}):
        current_genres = node.find_all('a', {'class': 'actionLinkLite bookPageGenreLink'})
        current_genre = ' > '.join([g.text for g in current_genres])
        if current_genre.strip():
            genres.append(current_genre)
    return genres


def get_isbn(soup):
    isbn = ''
    isbn_node = soup.find('div', {'class': 'infoBoxRowTitle'}, text='ISBN')
    if not isbn_node:
        isbn_node = soup.find('div', {'class': 'infoBoxRowTitle'}, text='ISBN13')
    if isbn_node:
        isbn = ' '.join(isbn_node.find_next_sibling().text.strip().split())
    return isbn.split()[0]


def get_rating_distribution(soup):
    distribution = re.findall(r'renderRatingGraph\([\s]*\[[0-9,\s]+', str(soup))[0]
    distribution = ' '.join(distribution.split())
    distribution = [int(c.strip()) for c in distribution.split('[')[1].split(',')]
    distribution_dict = {'5 Stars': distribution[0],
                         '4 Stars': distribution[1],
                         '3 Stars': distribution[2],
                         '2 Stars': distribution[3],
                         '1 Star':  distribution[4]}
    return distribution_dict


def get_num_pages(soup):
    if soup.find('span', {'itemprop': 'numberOfPages'}):
        num_pages = soup.find('span', {'itemprop': 'numberOfPages'}).text.strip()
        return int(num_pages.split()[0])
    return ''


def get_year_first_published(soup):
    year_first_published = soup.find('nobr', attrs={'class':'greyText'}).string
    return re.search('([0-9]{3,4})', year_first_published).group(1)


def scrape_book(book_id):
    url = 'https://www.goodreads.com/book/show/' + book_id
    source = urlopen(url)
    soup = bs4.BeautifulSoup(source, 'html.parser')

    time.sleep(2)

    return {'book_id':              book_id, 
            'isbn':                 get_isbn(soup), 
            'year_first_published': get_year_first_published(soup), 
            'title':                ' '.join(soup.find('h1', {'id': 'bookTitle'}).text.split()), 
            'author':               ' '.join(soup.find('span', {'itemprop': 'name'}).text.split()), 
            'num_pages':            get_num_pages(soup), 
            'genres':               get_genres(soup), 
            'shelves':              get_shelves(soup), 
            'lists':                get_all_lists(soup), 
            'num_ratings':          soup.find('meta', {'itemprop': 'ratingCount'})['content'].strip(), 
            'num_reviews':          soup.find('meta', {'itemprop': 'reviewCount'})['content'].strip(),
            'average_rating':       soup.find('span', {'itemprop': 'ratingValue'}).text.strip(), 
            'rating_distribution':  get_rating_distribution(soup)}


def main():

    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--book_ids_path', type=str)
    parser.add_argument('--output_directory_path', type=str)
    args = parser.parse_args()

    book_ids              = [line.strip() for line in open(args.book_ids_path, 'r') if line.strip()]
    books_already_scraped = [file_name.replace('.json', '') for file_name in os.listdir(args.output_directory_path)]
    books_to_scrape       = [book_id for book_id in book_ids if book_id not in books_already_scraped]

    for i, book_id in enumerate(books_to_scrape):
        try:
            print(str(datetime.now()) + ' ' + script_name + ': Scraping ' + book_id + '...')
            print(str(datetime.now()) + ' ' + script_name + ': #' + str(i+1+len(books_already_scraped)) + ' out of ' + str(len(book_ids)) + ' books')

            book = scrape_book(book_id)
            json.dump(book, open(args.output_directory_path + '/' + book_id + '.json', 'w'))

            print('=============================')

        except HTTPError as e:
            print(e)
            exit(0)

    print(str(datetime.now()) + ' ' + script_name + ': Run Time = ' + str(datetime.now() - start_time))


if __name__ == '__main__':
    main()
