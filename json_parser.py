import json
import os

import markdown
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 配置设置
app.config.from_pyfile("config.py" if os.path.exists("config.py") else "config.py.example")
db = SQLAlchemy(app)


# 模型定义
class JsonData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    schema = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<JsonData {self.id}>"


# 验证文件类型
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# 解析内容
def parse_content(content, schema):
    try:
        json_data = json.loads(content)
        return json.dumps(json_data, indent=4)
    except json.JSONDecodeError:
        return markdown.markdown(content)


# GUI 界面
@app.route('/gui', methods=['GET', 'POST'])
def gui():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == "":
            return render_template('gui.html', error='请选择文件')

        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            schema = request.form.get("schema", "{}")
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                return render_template('gui.html', error="无效的 Schema 格式")

            try:
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "r") as f:
                    content = f.read()
                result = parse_content(content, schema)
                return render_template('gui.html', result=result)
            except Exception as e:
                return render_template('gui.html', error=str(e))

        else:
            return render_template('gui.html', error="不允许的文件类型")

    return render_template('gui.html')


# Web 界面
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == "":
            return render_template('index.html', error='请选择文件')

        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            schema = request.form.get("schema", "{}")
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                return render_template('index.html', error="无效的 Schema 格式")

            try:
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "r") as f:
                    content = f.read()
                result = parse_content(content, schema)
                # 保存到数据库
                json_data = JsonData(content=content, schema=json.dumps(schema))
                db.session.add(json_data)
                db.session.commit()
                return render_template('index.html', result=result)
            except Exception as e:
                return render_template('index.html', error=str(e))

        else:
            return render_template('index.html', error="不允许的文件类型")

    return render_template('index.html')


# API 端点
@app.route('/api/parse', methods=['POST'])
def parse_api():
    file = request.files.get('file')
    schema = request.get_json().get('schema', {})

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        try:
            with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "r") as f:
                content = f.read()
            result = parse_content(content, schema)
            return jsonify({'result': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file'}), 400


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=app.config["DEBUG"])
