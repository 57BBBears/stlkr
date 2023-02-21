import sys
import json
from datetime import datetime
from scrapy import Selector
from sqlalchemy import bindparam
from app import create_app, db
from app.models import DataFrame, Check, UrlCheck
from stlkr import Stalker


app = create_app()
app.app_context().push()


# Functions for dataframe check - parsing urls
def check_dataframe(pk: int):
    try:
        check = Check.query.get(pk)
        app.logger.info(f'Task "check_dataframe" has started. Check: {check}.')
        if check:
            # get urls for check (only urls that haven't been checked yet due to a pause (future feature))
            all_urls = set(check.dataframe.urls)
            # TODO recheck urls with non 200 status ?
            checked_urls = {url.url_id for url in check.urls}
            unchecked_urls = {url.url: url.id for url in all_urls if url.id not in checked_urls}

            parsed_urls_count = 0
            if unchecked_urls:
                # Bound saving url to db as a callback to a parser spider and run parsing
                def save_url_to_db(item):
                    url_check = UrlCheck(check=check,
                                         url_id=unchecked_urls[item['url']],
                                         status=item['status'],
                                         raw_data=item['data']
                                         )
                    db.session.add(url_check)
                    db.session.commit()

                    nonlocal parsed_urls_count
                    parsed_urls_count += 1
                # TODO move to a separate function !
                spider = 'urls'
                stalker = Stalker(spider, start_urls=list(unchecked_urls.keys()))
                stalker[spider].handle_item(save_url_to_db)
                stalker[spider].handle_error(handle_crawling_error)
                stalker.run()

            check.end_time = datetime.utcnow()
            db.session.commit()

            app.logger.info(f'Task "check_dataframe" has finished successfully. Check: {check} '
                            f'All urls: {len(all_urls)}. Already checked: {len(checked_urls)}. '
                            f'Parsed {parsed_urls_count} urls.')
        else:
            app.logger.warning(f'Task "check_dataframe" has not started. No Check with pk: {pk}.')
    except Exception:
        app.logger.error('Task "check_dataframe" has crashed. Error: ', exc_info=True)


def handle_crawling_error(item, response, spider, failure):
    app.logger.error(f'Item {item} error: {failure}. Status: {response.status}. Spider: {spider}.')


# Functions for retrieving data from a parsed url html
def extract_data_from_check(pk: int, urls_per_check: int = None, only_new=False):
    try:
        check = Check.query.get(pk)
        app.logger.info(f'Task "extract_data_from_check" has started. Check: {check}.')
        if check:
            # get check selectors
            try:
                selectors_dict = json.loads(check.selectors)
            except json.JSONDecodeError:
                app.logger.error('Task "extract_data_from_check" can\'t load selectors. Error: ', exc_info=True)
                sys.exit()

            # get parsed urls for extracting data
            parsed_urls = check.urls.filter_by(status=200)
            if only_new:
                parsed_urls = parsed_urls.filter_by(extracted_data='')
            if urls_per_check is not None:
                parsed_urls = parsed_urls.limit(urls_per_check)

            data = []
            while parsed_urls:
                for url in parsed_urls:
                    data.append(
                        {'id': url.id, 'data': json.dumps(  # TODO check empty data?
                            parse_data_by_xpath(url.raw_data, selectors_dict)
                        )}
                    )

                # update CheckUrls in DB
                save_extracted_data_to_db(data)
                db.session.commit()
            app.logger.info(f'Task "extract_data_from_check" has finished successfully. Check: {check}')
        else:
            app.logger.warning(f'Task "extract_data_from_check" has not started. No Check with pk: {pk}.')
    except Exception:
        app.logger.error('Task "check_extract_parsed_data" has crashed. Error: ', exc_info=True)


def save_extracted_data_to_db(data: list[dict[int, str]]):
    stmt = get_update_urlcheck_extracted_data_sql()
    db.session.execute(stmt, data)


def get_update_urlcheck_extracted_data_sql():
    check_table = Check.__table__

    return (
        check_table.update()
        .where(check_table.c.id == bindparam('id'))
        .values(extracted_data=bindparam('data'))
    )


def parse_data_by_xpath(source: str, selectors: dict) -> dict:
    body = Selector(text=source)

    return {name: body.xpath(selectors[name]).getall() for name in selectors}
