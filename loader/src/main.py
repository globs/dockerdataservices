from manager.load_config_manager import LoaderConfigManager
import logging
import common.settings
import traceback

def main():
    try:
        common.settings.init_logging()
        config_manager = LoaderConfigManager()
        config_manager.apply_json(common.settings.db_transfers)
    except:
        logging.error(traceback.format_exc())

	


if __name__ == '__main__':
    main()
