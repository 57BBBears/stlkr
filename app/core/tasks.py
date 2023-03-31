from datetime import datetime
from app import create_app, db
from app.core.models import Check, UrlCheck, DataFrameProperty, UrlProperty
from app.core.utils import parse_data_by_xpath
from stlkr import Stalker

app = create_app()
app.app_context().push()

# Functions for dataframe check - parsing urls
def check_dataframe(pk: int):
    try:
        check = Check.query.get(pk)
        app.logger.info(f'Task "check_dataframe" has started. Check: {check}.')
        if check:
            # get urls for check (only urls that haven't been checked yet due to a pause or new ones)
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
    except Exception as e:
        app.logger.error(f'Task "check_dataframe" has crashed. Error: {e}', exc_info=True)

def handle_crawling_error(item, response, spider, failure):
    app.logger.error(f'Item {item} error: {failure}. Status: {response.status}. Spider: {spider}.')


# Functions for retrieving data from a parsed url html
def extract_data_from_check(pk: int, urls_per_check: int = None, only_new : bool = True):
    try:
        check = Check.query.get(pk)
        app.logger.info(f'Task "extract_data_from_check" has started. Check: {check}.')
        if check:
            # get parsed urls for extracting data
            parsed_urls = UrlCheck.query.filter_by(check=check, status=200)
            if only_new:
                parsed_urls = parsed_urls.outerjoin(UrlProperty,
                                                    UrlCheck.check_id==UrlProperty.check_id
                                                    ).filter(UrlProperty.data.is_(None))
            if urls_per_check is not None:
                parsed_urls = parsed_urls.limit(urls_per_check)

            if not only_new:
                # delete old data
                db.session.execute(UrlProperty.__table__.delete().where(UrlProperty.check_id==check.id))
                db.session.commit()

            selectors = get_dataframe_selectors(check.dataframe.id)
            data = []
            for url in parsed_urls:
                extracted_data = parse_data_by_xpath(url.raw_data, selectors)
                for property_id, prop_data in extracted_data.items():
                    if prop_data:
                        data.append({'check_id': url.check_id,
                                     'url_id': url.url_id,
                                     'property_id': property_id,
                                     'data': prop_data})
                # TODO add limited bulk update
                # insert new data into a database
                db.session.execute(UrlProperty.__table__.insert(), data)
                db.session.commit()
                data = []
            app.logger.info(f'Task "extract_data_from_check" has finished successfully. Check: {check}')
        else:
            app.logger.warning(f'Task "extract_data_from_check" has not started. No Check with pk: {pk}.')
    except Exception as e:
        app.logger.error(f'Task "check_extract_parsed_data" has crashed. Error: {e}', exc_info=True)

def get_dataframe_selectors(df_id):
    df_properties = DataFrameProperty.query.filter_by(dataframe_id=df_id).all()
    return {prop.property_id: prop.selector for prop in df_properties}

