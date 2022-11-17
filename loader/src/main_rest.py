from flask import send_file
from flask import Flask
from flask import request
from flask_cors import CORS
import io, json 
import base64
import common.settings
import logging
from manager.load_config_manager import LoaderConfigManager

#Actual flask code
app = Flask(__name__)
cors = CORS(app)
app.debug = True
loaderManager = LoaderConfigManager()

@app.route('/api/v1/docs',methods = ['POST', 'GET'])
def get_docs():
    return 'docs to be done'

    

@app.route('/api/v1/runjob_manual',methods = ['POST', 'GET'])
def run_job_manual():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json_dict = request.json
        run_results = loaderManager.apply_json(json.dumps(json_dict))
        return run_results
    else:
        return f'Content-Type {content_type} not supported! application/json expected'


if __name__=="__main__":
    common.settings.init_logging()
    app.run(debug=True, host='0.0.0.0',port='3333')
#else:
#    gunicorn_logger = logging.getLogger('gunicorn.error')
#    app.logger.handlers = gunicorn_logger.handlers
#    app.logger.setLevel(gunicorn_logger.level)

