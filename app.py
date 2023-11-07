import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, render_template, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime
from bson import ObjectId

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]


app = Flask(__name__)

@app.route('/')
def main():
    words_result = db.words.find({}, {'_id': False})
    words = []
    for word in words_result:
        definisi = word['definisi'][0]['shortdef']
        definisi = definisi if type(definisi) is str else definisi[0]
        words.append({
            'word': word['word'],
            'definisi': definisi,
        })
    msg = request.args.get('msg')
    return render_template('index.html', words=words, msg=msg)


@app.route('/error')
def error():
    # Mengambil pesan kesalahan dari parameter URL
    msg = request.args.get('msg')
    # Mendapatkan saran kata-kata
    suggestions = request.args.get('suggestions')
    # Membagi kata-kata menjadi daftar
    suggestions = suggestions.split(', ') if suggestions else []
    # Mengirim pesan kesalahan ke template error.html
    return render_template('error.html', msg=msg, suggestions=suggestions)


@app.route('/detail/<keyword>')
def detail(keyword):
    api_key = "a5fc0962-e8b2-4adf-b1dc-a0517598e2d2"

    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{keyword}?key={api_key}'
    response = requests.get(url)
    definisi = response.json()

    # cek word apakah sudah tersimpan ke database
    word_saved = db.words.find_one({'word': keyword})
    # if not word_saved:
    #     return redirect(url_for('main', msg=f'Word "{keyword}" is not saved in the database'))

    if not definisi:
        return redirect(url_for(
            'error',
            msg=f'Could not find the word, "{keyword}"'
        ))

    if type(definisi[0]) is str:
        # Menyimpan saran kata-kata sebagai string
        suggestions = ', '.join(definisi)
        return redirect(url_for(
            'error',
            msg=f'Could not find the word, "{keyword}", did you mean: {suggestions}',
            suggestions=suggestions  # Mengirim saran kata-kata ke halaman error sebagai string
        ))

    status = request.args.get('status_give', 'new')
    return render_template('detail.html', word=keyword, definisi=definisi, status=status, word_saved=word_saved)


# route api murni/ simpan kata
@app.route('/api/save_word', methods=['POST'])
def save_word():
    json_data = request.get_json()
    word = json_data.get('word_give')
    definisi = json_data.get('definisi_give')

    doc = {
        'word': word,
        'definisi': definisi,
        'date': datetime.now().strftime('%Y%m%d'),
    }

    db.words.insert_one(doc)

    return jsonify({
        'result': 'success',
        'msg': f'Kata, {word}, berhasil disimpan',
    })

# route api hapus data


@app.route('/api/delete_word', methods=['POST'])
def delete_word():
    word = request.form.get("word_give")
    
    # Hapus kata dari koleksi 'words'
    db.words.delete_one({"word": word})
    
    # Hapus semua contoh kalimat terkait dengan kata tersebut
    db.examples.delete_many({'word': word})
    
    return jsonify({
        'result': 'success',
        'msg': f'the word {word} and its examples were deleted'
    })





@app.route('/api/get_exs', methods=['GET'])
def get_exs():
    word = request.args.get('word')
    example_data = db.examples.find({'word': word})
    examples = []
    for example in example_data:
        examples.append({
            'example': example.get('example'),
            'id': str(example.get('_id')),
        })
    return jsonify({'result': 'success', 'examples': examples})



@app.route('/api/save_ex', methods=['POST'])
def save_ex():
    word = request.form.get('word')
    example = request.form.get('example')

    doc = {
        'word': word,
        'example': example,
    }
    db.examples.insert_one(doc)
    return jsonify({'result': 'success', 'msg': f'Example sentence added for the word "{word}"'})

@app.route('/api/delete_ex', methods=['POST'])
def delete_ex():
    id = request.form.get('id')
    word = request.form.get('word')
    db.examples.delete_one({'_id': ObjectId(id)})
    return jsonify({'result': 'success', 'msg': f'Example sentence deleted for the word "{word}"'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)


# import requests

# api_key = 'a5fc0962-e8b2-4adf-b1dc-a0517598e2d2'
# word = 'tomato'
# url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}'

# res = requests.get(url)

# definisi = res.json()

# for definisi in definisi:
#     print(definisi)
