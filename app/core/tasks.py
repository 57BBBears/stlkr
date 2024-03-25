import sys
from datetime import datetime
from sqlalchemy import exists, and_
from sqlalchemy.orm import Query
from app import db
from app.models import Url, Check, UrlCheck, DataframeProperty, UrlProperty
from app.core.utils import parse_data_by_xpath
from stlkr import Stalker
from logging import getLogger

logger = getLogger(__name__)


def check_dataframe(pk: int):
    """ Function for dataframe check - parsing urls. """
    try:
        check = Check.query.get(pk)
        logger.info(f'Task "check_dataframe" has started. Check: {check}.')
        if check:
            # get urls for check (only urls that haven't been checked yet due to a pause or new ones)
            #all_urls = set(check.dataframe.urls)
            all_urls_count = db.session.query(Url.id).filter_by(dataframe_id=check.dataframe.id).count()
            checked_urls_count = db.session.query(UrlCheck.id).filter_by(check_id=pk).count()
            # TODO recheck urls with non 200 status ?
            #checked_urls = {url.url_id for url in check.urls}
            unchecked_urls = get_unchecked_urls_stmt(pk).all()
            unchecked_urls = {url: url_id for url_id, url in unchecked_urls}

            parsed_urls_count = 0
            if unchecked_urls:
                # Bound saving url to db as a callback to a parser spider and run parsing
                def save_url_to_db(item):
                    if item['url'] in unchecked_urls:  # prevent url changing or some encoded signs in the url

                        db.session.add(UrlCheck(check=check,
                                             url_id=unchecked_urls[item['url']],
                                             status=item['status'],
                                             raw_data=item['data']
                                             ))
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
            db.session.close()

            logger.info(f'Task "check_dataframe" has finished successfully. Check: {check} '
                            f'All urls: {all_urls_count}. Already checked: {checked_urls_count}. '
                            f'Parsed {parsed_urls_count} urls.')
        else:
            logger.warning(f'Task "check_dataframe" has not started. No Check with pk: {pk}.')
    except Exception as e:
        logger.error(f'Task "check_dataframe" has crashed. Error: {e}', exc_info=True)

def get_unchecked_urls_stmt(check_id: int, limit: int = None):
    """ Select urls that don't have parsed data. """
    df_id = db.session.query(Check.dataframe_id).filter_by(id=check_id).scalar_subquery()

    unchecked_urls_stmt = db.session.query(
        Url.id, Url.url
    ).where(and_(Url.dataframe_id==df_id, ~exists().where(Url.id==UrlCheck.url_id, UrlCheck.check_id==check_id)))

    if limit:
        unchecked_urls_stmt = unchecked_urls_stmt.limit(limit)

    return unchecked_urls_stmt

def handle_crawling_error(item, response, spider, failure):
    logger.error(f'Item {item} error: {failure}. Status: {response.status}. Spider: {spider}.')

def extract_data_from_check(pk: int, urls_per_extract: int, max_urls: int = None, only_new : bool = True):
    """ A function for retrieving data from a parsed url html """
    # TODO add option extracting fixed parts of the selectors with regexp i.e. {url} {site} etc set in DataframeProperty
    try:
        check = Check.query.get(pk)
        if check:
            logger.info(f'Task "extract_data_from_check" has started. Check: {check}.')
        else:
            logger.warning(f'Task "extract_data_from_check" has not started. No Check with pk: {pk}.')
            sys.exit()

        if not only_new:
            # delete old data
            db.session.execute(UrlProperty.__table__.delete().where(UrlProperty.check_id == check.id))
            db.session.commit()

        if max_urls:
            limit = min(max_urls, urls_per_extract)
        else:
            limit = urls_per_extract
            max_urls = float('inf')

        urls_count, parsed_urls_count = 0, 0
        offset = 0 # set offset to avoid selecting the same urls with empty selectors

        # getting parsed urls for extracting data
        while (parsed_urls := get_checked_urls_stmt(pk, True, limit, offset).all()) and urls_count < max_urls:
            cur_urls_count = len(parsed_urls)
            parsed_urls_count += cur_urls_count
            logger.debug(f'Extracted {cur_urls_count} urls.')

            urls_count += limit

            selectors = get_dataframe_selectors(check.dataframe.id)
            data = []
            for url in parsed_urls:
                extracted_data = parse_data_by_xpath(url.raw_data, selectors)
                for property_id, prop_data in extracted_data.items():
                    if prop_data:
                        data.append({'check_id': check.id,
                                     'url_id': url.url_id,
                                     'property_id': property_id,
                                     'data': prop_data})
                # TODO add limited bulk update
                if data:
                    # insert new data into a database
                    db.session.execute(UrlProperty.__table__.insert(), data)
                    db.session.commit()
                    data = []
                else:
                    offset += 1 # do not check an url without data again

            logger.debug(f'Data for extracted urls saved.')
        logger.info(f'Task "extract_data_from_check" has finished successfully. Check: {check}. '
                        f'Handled {parsed_urls_count} urls.')

    except Exception as e:
        logger.error(f'Task "check_extract_parsed_data" has crashed. Error: {e}', exc_info=True)

def get_checked_urls_stmt(check_id, only_new : bool = True, limit: int = 0, offset: int = 0) -> Query:
    """ Get UrlChecks with parsed raw_data to extract selectors from there. """
    parsed_urls = UrlCheck.query.filter(UrlCheck.check_id==check_id, UrlCheck.status==200, UrlCheck.raw_data!='')

    if only_new:
        parsed_urls = parsed_urls.where(~exists().where(
            UrlCheck.check_id==UrlProperty.check_id, UrlCheck.url_id==UrlProperty.url_id))
        """
        parsed_urls = parsed_urls.outerjoin(UrlProperty,
                                            UrlCheck.check_id == UrlProperty.check_id
                                            ).filter(UrlProperty.data.is_(None))
        """

    if limit:
        parsed_urls = parsed_urls.limit(limit)

    if offset:
        parsed_urls = parsed_urls.offset(offset)

    return parsed_urls

def get_dataframe_selectors(df_id: int) -> dict[int, str]:
    """ Return property selectors of the dataframe. """
    df_properties = DataframeProperty.query.filter_by(dataframe_id=df_id).all()
    return {prop.property_id: prop.selector for prop in df_properties}
