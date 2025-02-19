# Database Connector Main for all database connections
# contributor: smlee

# History
# 2024-12-22 | v1.3 - add SQLite, removed dataclass, and log bug fix
# 2024-04-21 | v1.2 - add logger
# 2024-03-28 | v1.1 - add insert method
# 2024-03-27 | v1.0 - first commit

# Module import
from pydb.util.mysql import mariaConnect
from pydb.util.mongo import mongoConnect
from pydb.util.azure import AzureTable
from pydb.util.sqlite import SQLiteConnect
from pydb.conf.logger import log, Logger
log_config = Logger(name='pydb',verbose=1)
log_config.clear_log_content()
logger = log_config.get_logger()
from .func.create_db_pool import DBPool
from .func.get_secrets import get_secret
from typing import List, Union, Dict
import asyncio

# Main
class Database:
    """Database connection class
    
    Args:
        database: database name
        * current database list:
            - mariadb/mysql
            - mongodb
            - azure
            - sqlite (will be integrated soon, refer util for now)
            - postgresql (coming soon)
        override: optional argument
    """

    def __init__(self,
                 name:str,
                 *,
                 path:str=str(),
                 vault:bool=False):
        # configuration
        self.name = name
        
        # database setting
        secret = get_secret(self.name,path=path,vault=vault)

        if self.name == "mariadb" or self.name == "mysql":
            self.database = mariaConnect(DBPool(secret),True)

        elif self.name == "mongodb":
            self.database = mongoConnect(secret)
            
        elif self.name == "azure":
            self.database = AzureTable(secret)
        
        elif self.name == "sqlite":
            self.database = SQLiteConnect(secret)
            
    def __enter__(self):
        """Instantiate mariaConnect class object"""

        return self
    
    def __exit__(self,
                 exception_type,
                 exception_value,
                 traceback):
        """Exit instantiation from __enter__
        """

        self.database.close()

        if not exception_type:
            return True
        else:
            raise BaseException(f"Exit error: {exception_type}, {exception_value}, {traceback}")
    @log(set_logger=logger)      
    def select(self,
               *,
               query:str=None,
               database:str=None,
               features:list=None,
               parameters:dict=None,
               name_filter:str=None,
               table_name:str=None,
               collection_name:str=None) -> List:
        """Execute SELECT command from MariaDB or findall from MongoDB or query entity from Azure Table Storage 
        using either input query (MariaDB) or conditions (MongoDB) or entity (Azure Table Storage) 

        Args:
            For MariaDB,
                query: a query for MariaDB
                database (optional): database name for MariaDB // table_name for Azure Table
            For MongoDB,
                query: a query for MongoDB
                collection_name: a collection name for MongoDB
                database (optional): a database name for MongoDB
            For AzureTable,
                features: a list of columns to select from Azure Table (named select)
                parameters: a dictionary of parameters for Azure Table
                name_filter: a filter for Azure Table
                database: a table name for Azure Table
            For SQLite,
                table_name (required): a table name for SQLite
                features (required): a list of columns to select from SQLite
                parameters (optional): a filter for SQLite 
        Returns:
            list(rows matched conditions)
        """

        try:
            if self.name == "mariadb":
                assert query
                return self.database.select(query,database)
            elif self.name == "mongodb":
                assert query
                assert collection_name
                return self.database.find(query,collection_name)
            elif self.name == "azure":
                assert features
                assert parameters
                assert name_filter
                return asyncio.run(self.database.query_entity(select=features,
                                                              parameters=parameters,
                                                              name_filter=name_filter,
                                                              table_name=database))
            elif self.name == "sqlite":
                assert table_name
                assert features
                return self.database.select(table_name=table_name,
                                            columns=features,
                                            conditions=parameters)
        except:
            return log_config.get_log_content()
    @log(set_logger=logger)
    def insert(self,
               *,
               data:Union[List,Dict]=None,
               table_name:str=None,
               collection_name:str=None,
               database:str=None,
               is_merge_mode:bool=False):
        """Insert data into the database
        
        Args:
            For MariaDB,
                data (List|Dict): data
                table_name (str): table name
                database (optional): database name for MariaDB // table_name for Azure Table
            For MongoDB,
                data (List|Dict): data
                collection_name: a collection name for MongoDB
                database (optional): a database name for MongoDB
                is_merge_mode (bool): whether to use merge mode
            For AzureTable,
                data (List|Dict): data
                database: a table name for Azure Table
            For SQLite,
                data (List|Dict): data
                table_name (str): table name
        
        """
        try:
            if self.name == "mariadb":
                    assert data
                    assert table_name
                    if is_merge_mode:
                        self.database.merge(data=data,
                                            table_name=table_name,
                                            database=database)
                    else:
                        self.database.insert(data=data,
                                             table_name=table_name,
                                             database=database)
            elif self.name == "mongodb":
                assert data
                assert collection_name
                if database:
                    self.database.insert(rows=data,
                                         collection_name=collection_name,
                                         database=database,
                                         is_merge_mode=is_merge_mode)
                else:
                    self.database.insert(rows=data,
                                         collection_name=collection_name,
                                         is_merge_mode=is_merge_mode)
            elif self.name == "azure":
                assert data
                assert database
                asyncio.run(self.database.insert_entity(entity=data,
                                                        table_name=database))
            elif self.name == "sqlite":
                assert data
                assert table_name
                self.database.insert(table_name=table_name,
                                     values=data)
        except:
            return log_config.get_log_content()
        
    def close(self):
        """Close database connection"""
        self.database.close()