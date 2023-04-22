from scrapy import Selector

def clear_url(url: str) -> str:
    if url := str(url).strip().lower():
        url_start = url.find(' ') + 1
        if url_start:
            url = url[url_start:].strip()

    return url


def text_to_list(text: str, sep='\r\n') -> list:
    text_list = text.split(sep)

    return [x for x in map(clear_url, text_list) if x]

def populate_object(obj, form, exclude=[]):
    for field_name, field_value in form._fields.items():
        if field_name in exclude:
            continue

        if hasattr(obj, field_name):
            setattr(obj, field_name, field_value.data)

def parse_data_by_xpath(source: str, selectors: dict) -> dict[int, str]:
    """ Return data as dict with given keys from selectors dict as keys
    and extracted data as a value {selectors[id]: extarcted_data} """
    data = {}
    body = Selector(text=source)
    for sel_id, selector in selectors.items():
        ext_data = body.xpath(selector).getall()
        if ext_data and len(ext_data) == 1:
            ext_data = ext_data[0]
        # add only nonempty values
        if ext_data:
            data[sel_id] = ext_data

    return data