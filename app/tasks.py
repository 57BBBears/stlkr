from app import create_app, db
from app.models import DataFrame, Check, UrlCheck
from datetime import datetime
from stlkr import Stalker


app = create_app()
app.app_context().push()


def check_dataframe(pk):
    try:
        check = Check.query.get(pk)
        app.logger.info(f'Task "check_dataframe" has started. Check: {check}.')
        if check:
            # get urls for checking (only urls that haven't been checked yet)
            all_urls = set(check.dataframe.urls)
            # TODO recheck urls with non 200 status ?
            checked_urls = {url.url_id for url in check.urls}
            unchecked_urls = {url.url: url.id for url in all_urls if url.id not in checked_urls}

            parsed_urls_count = 0
            if unchecked_urls:
                # Connect saving url to db as callback with a parser spider and run parsing
                def save_url_to_db(item):
                    url_check = UrlCheck(check=check,
                                         url_id=unchecked_urls[item['url']],
                                         status=item['status'],
                                         data=item['data']
                                         )
                    db.session.add(url_check)
                    db.session.commit()

                    nonlocal parsed_urls_count
                    parsed_urls_count += 1

                spider = 'urls'
                stalker = Stalker(spider, start_urls=list(unchecked_urls.keys()))
                stalker[spider].handle_item(save_url_to_db)
                stalker[spider].handle_error(handle_crawling_error)
                stalker.run()
            """
            # write urls data to db     
        urls_data = None
            if urls_data:
                # TODO set urls_per_check and write to db bulk in loop ?
                db.session.execute(UrlCheck.__table__.insert(), [
                    {'url_id': unchecked_urls[url],
                     'check_id': check.id,
                     'status': data['status'],
                     'data': data['data'] if data['status'] == 200 else ''
                     } for (url, data) in urls_data.items()]
                )            
            """
            check.end_time = datetime.utcnow()
            db.session.commit()

            app.logger.info(f'Task "check_dataframe" has finished. Check: {check} '
                            f'All urls: {len(all_urls)}. Already checked: {len(checked_urls)}. '
                            f'Parsed {parsed_urls_count} urls.')
    except Exception:
        app.logger.error('Task "check_dataframe" has crashed.', exc_info=True)


def handle_crawling_error(item, response, spider, failure):
    app.logger.error(f'Item {item} error: {failure}. Status: {response.status}. Spider: {spider}.')
