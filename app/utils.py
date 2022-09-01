def clear_url(url: str) -> str:
    if url := str(url).strip().lower():
        url_start = url.find(' ') + 1
        if url_start:
            url = url[url_start:].strip()

    return url


def text_to_list(text: str, sep='\r\n') -> list:
    text_list = text.split(sep)

    return [x for x in map(clear_url, text_list) if x]
