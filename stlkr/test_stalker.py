import pytest
from pytest import fixture
from stlkr import Stalker


@fixture
def start_urls():
    return {
        'empty': [],
        'empty_str': '',
        1: ['https://ya.ru'],
        2: ['https://ya.ru', 'https://google.com'],
        200: ['https://quotes.toscrape.com'],
        'str_2': 'https://ya.ru,https://google.com',
        'str_with_blank': 'https://ya.ru, https://google.com'
    }


@fixture
def get_spider_name():
    return 'urls'


@fixture
def stalker(get_spider_name, start_urls):
    stalker = {}
    for name in start_urls:
        stalker[name] = Stalker(get_spider_name, start_urls=start_urls[name])

    return stalker


class TestStalker:
    def test_init_without_spider_name(self, get_spider_name):
        stlkr = Stalker()
        assert stlkr.all() == ['test', get_spider_name]
        assert stlkr.list() == []

    def test_init_with_spider_name(self, get_spider_name, stalker):
        assert stalker[1].list() == [get_spider_name]

    def test_start_urls_dif_types(self, get_spider_name, stalker):
        spider = get_spider_name
        assert stalker['empty'][spider].params == {'start_urls': []}
        assert stalker['empty_str'][spider].params == {'start_urls': ''}
        assert stalker[2][spider].params == {'start_urls': ['https://ya.ru', 'https://google.com']}
        assert stalker['str_2'][spider].params == {'start_urls': 'https://ya.ru,https://google.com'}
        assert stalker['str_with_blank'][spider].params == {'start_urls': 'https://ya.ru, https://google.com'}

    def test_add_spider(self, get_spider_name, stalker):
        stlkr = stalker[1]
        assert stlkr.list() == [get_spider_name]
        stlkr.add('test')
        assert stlkr.list() == [get_spider_name, 'test']
        # add non existing spider
        with pytest.raises(ValueError):
            stlkr.add('non_existing')

    def test_remove_spider(self, get_spider_name, stalker):
        stlkr = stalker['empty']
        assert stlkr.list() == [get_spider_name]
        stlkr.remove(get_spider_name)
        assert stlkr.list() == []

    def test_run(self, get_spider_name, start_urls, stalker):
        def stalker_item_callback(item):
            assert item['status'] == 200
            assert item['url'] == start_urls[200]
            assert '<html>' in item['text']

        stlkr = stalker[200]
        stlkr[get_spider_name].handle_item(stalker_item_callback)
        stlkr.run()

    def test_all(self, get_spider_name, stalker):
        assert stalker['empty'].all() == ['test', get_spider_name]

    def test_list(self, get_spider_name, stalker):
        assert stalker['empty'].list() == [get_spider_name]
        stlkr = Stalker()
        assert stlkr.list() == []
