import sys
import os
import pandas as pd
import pandas.core.frame as pd_frame
import pandas.errors as pd_errors
from typing import overload

import pandas.errors

from bin.settings import TEMP_CSV_DIR, clr
from simple_salesforce import Salesforce


class SalesforceCommands:

    def __init__(self, username: str, password: str, security_token: str, domain: str = None, consumer_key: str = None, privatekey_file: str = None):
        """
        Provide login credentials to the Org that You want to authorize. Domain is optional, but
        You have to provide 'test' if You want to authorize sandbox Org.

        :param username:
        :param password:
        :param security_token:
        :param domain:
        :param consumer_key:
        :param privatekey_file:
        """
        try:
            clr.print_info(f">> Authorizing an Org {username}")
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain if domain else None,
                consumer_key=consumer_key,
                privatekey_file=privatekey_file
            )
            clr.print_success(">> Org authorized successful")
        except Exception as e:
            clr.print_error(">> Error during authorizing an Org")
            clr.print_error(f">> {e}")
            sys.exit()

    def get_bulk(self, query: str, s_object: str, file_name=None) -> pd_frame.DataFrame:
        clr.print_info(f">> Running bulk query for {s_object} object")
        if file_name is None:
            file_name = f"{s_object}_get_bulk.csv"
        try:
            fetch_results = self.sf.bulk.__getattr__(s_object).query(query, lazy_operation=True)
        except Exception as e:
            clr.print_error(f">> {e}")
            return None

        data = []
        result_df = pd.DataFrame()
        for list_results in fetch_results:
            data.extend(list_results)
        if len(data) > 0:
            result_df = pd.DataFrame.from_records(data).drop('attributes', axis=1)
        else:
            clr.print_info(">> There is no records matching query")

        result_df.to_csv(os.path.join(TEMP_CSV_DIR, file_name), index=False)

        clr.print_success(f">> Query ended successful with {len(result_df.index)} rows")
        return result_df

    def delete_bulk(self, s_object: str, dataframe: pd_frame.DataFrame = None, path: str = "generate_from_temp",
                    batch_size: int = 10000, use_serial: bool = True) -> bool:
        """
        Function require sObject type which should be deleted and data with record's ID to delete (Dataframe or path to CSV file, both must have 'Id' column).
        If source is not provided, function will take CSV from get_bulk function for provided sObject.

        :param s_object:
        :param dataframe:
        :param path:
        :param batch_size:
        :param use_serial:
        :return:
        """
        if dataframe is None:
            if path == "generate_from_temp":
                path = os.path.join(TEMP_CSV_DIR, f"{s_object}_get_bulk.csv")
            if not os.path.isfile(path):
                clr.print_error(f">> There is no file in the given path {path}")
                return False
            clr.print_info(f">> Running bulk delete {s_object} from CSV file")
            try:
                dataframe = pd.read_csv(filepath_or_buffer=path)
            except pd_errors.EmptyDataError:
                clr.print_error(">> CSV file is empty")
                return False
            except Exception as e:
                clr.print_error(f">> {e}")
                return False
        else:
            clr.print_info(f">> Running bulk delete {s_object} from Pandas DataFrame")

        data = dataframe[['Id']].to_dict('records')
        clr.print_info(f">> {len(data)} records prepared to delete")

        if len(data) == 0:
            clr.print_info(f">> No {s_object} records to delete")
            return False

        try:
            result = self.sf.bulk.__getattr__(s_object).delete(data, batch_size=batch_size, use_serial=use_serial)
        except Exception as e:
            clr.print_error(f">> {e}")
            return False

        success, failure = 0, 0
        for res in result:
            if res['success']:
                success += 1
            else:
                failure += 1

        clr.print_info(f">> Succesfully deleted {success} records, {failure} records failed")
        clr.print_success(">> Deleting ended succesful")
        return True


if __name__ == '__main__':
    sf = SalesforceCommands(
        username='',
        password='',
        security_token='',
        domain=''
    )
    df = sf.get_bulk(query="SELECT Id, Name FROM Account WHERE Id =''", s_object="Account")
    sf.delete_bulk(s_object="Account")
