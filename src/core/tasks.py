import sys
from datetime import datetime, timezone

from src import create_app
from src.core.utils.query import (
    get_checked_urls_stmt,
    get_dataframe_selectors,
    get_unchecked_urls_stmt,
)
from src.core.utils.text import parse_data_by_xpath
from src.models import Check, Url, UrlCheck, UrlProperty, db
from src.stalker import Stalker

app = create_app()
app.app_context().push()


def check_dataframe(pk: int):
    """Function for dataframe check - parsing urls."""
    try:
        app.logger.info(f'Task "check_dataframe" has started. Check id: {pk}.')
        check = Check.query.get(pk)
        if check:
            # get urls for check (only urls that haven't been checked yet due to a pause
            # or new ones)
            # all_urls = set(check.dataframe.urls)
            all_urls_count = (
                db.session.query(Url.id)
                .filter_by(dataframe_id=check.dataframe.id)
                .count()
            )
            checked_urls_count = (
                db.session.query(UrlCheck.id).filter_by(check_id=pk).count()
            )
            # TODO recheck urls with non 200 status ?
            # checked_urls = {url.url_id for url in check.urls}
            unchecked_urls = get_unchecked_urls_stmt(pk).all()
            unchecked_urls = {url: url_id for url_id, url in unchecked_urls}

            parsed_urls_count = 0
            if unchecked_urls:
                # Bound saving url to db as a callback to a parser spider and
                # run parsing
                def save_url_to_db(item):
                    if (
                        item["url"] in unchecked_urls
                    ):  # prevent url changing or some encoded signs in the url
                        db.session.add(
                            UrlCheck(
                                check=check,
                                url_id=unchecked_urls[item["url"]],
                                status=item["status"],
                                raw_data=item["data"],
                            )
                        )
                        db.session.commit()

                        nonlocal parsed_urls_count
                        parsed_urls_count += 1

                # TODO move to a separate function !
                spider = "urls"
                stalker = Stalker(spider, start_urls=list(unchecked_urls.keys()))
                stalker[spider].handle_item(save_url_to_db)
                stalker[spider].handle_error(
                    lambda item, response, spider_, failure: app.logger.error(
                        f"Item {item} error: {failure}. Status: {response.status}. "
                        f"Spider: {spider_}."
                    )
                )
                stalker.run()

            check.end_time = datetime.now(timezone.utc)

            db.session.commit()
            db.session.close()

            app.logger.info(
                f'Task "check_dataframe" has finished successfully. Check: {check} '
                f"All urls: {all_urls_count}. Already checked: {checked_urls_count}. "
                f"Parsed {parsed_urls_count} urls."
            )
        else:
            app.logger.warning(
                f'Task "check_dataframe" has not started. No Check with pk: {pk}.'
            )
    except Exception as e:
        app.logger.error(
            f'Task "check_dataframe" has crashed. Error: {e}', exc_info=True
        )


def extract_data_from_check(pk: int, only_unchecked: bool = True, max_urls: int = None):
    """
    Retrieving data from a parsed url html
    :param pk: Check id
    :param only_unchecked: weather extract data from unchecked urls or cancel previous
    extraction and reextract all urls again
    :param max_urls: max amount of handling urls
    :return:
    """
    """"""
    # TODO add option extracting fixed parts of the selectors with regexp i.e.
    #  {url} {site} etc set in DataframeProperty
    try:
        check = Check.query.get(pk)
        if check:
            app.logger.info(
                f'Task "extract_data_from_check" has started. Check: {check}.'
            )
        else:
            app.logger.warning(
                f'Task "extract_data_from_check" has not been started. '
                f"No Check with pk: {pk}."
            )
            sys.exit()

        if not only_unchecked:
            # delete old data
            db.session.execute(
                UrlProperty.__table__.delete().where(UrlProperty.check_id == check.id)
            )
            db.session.commit()

        if max_urls:
            limit = min(app.config["URLS_PER_EXTRACT"], max_urls)
        else:
            limit = app.config["URLS_PER_EXTRACT"]
            max_urls = float("inf")

        urls_count, parsed_urls_count = 0, 0
        offset = 0  # set offset to avoid selecting the same urls with empty selectors

        # getting parsed urls for extracting data
        while (
            parsed_urls := get_checked_urls_stmt(pk, True, limit, offset).all()
        ) and urls_count < max_urls:
            cur_urls_count = len(parsed_urls)
            parsed_urls_count += cur_urls_count
            app.logger.debug(f"Extracted {cur_urls_count} urls.")

            urls_count += limit

            selectors = get_dataframe_selectors(check.dataframe.id)
            data = []
            for url in parsed_urls:
                extracted_data = parse_data_by_xpath(url.raw_data, selectors)
                for property_id, prop_data in extracted_data.items():
                    if prop_data:
                        data.append(
                            {
                                "check_id": check.id,
                                "url_id": url.url_id,
                                "property_id": property_id,
                                "data": prop_data,
                            }
                        )
                # TODO add limited bulk update
                if data:
                    # insert new data into a database
                    db.session.execute(UrlProperty.__table__.insert(), data)
                    db.session.commit()
                    data = []
                else:
                    offset += 1  # do not check an url without data again

            app.logger.debug("Data for extracted urls saved.")
        app.logger.info(
            f'Task "extract_data_from_check" has finished successfully. Check: {check}.'
            f" Handled {parsed_urls_count} urls."
        )

    except Exception as e:
        app.logger.error(
            f'Task "check_extract_parsed_data" has crashed. Error: {e}', exc_info=True
        )
