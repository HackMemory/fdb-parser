#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    @Author: github.com/hackmemory
"""

from functools import reduce
import json
import random
import xml.etree.ElementTree as ET
import re
import binascii
import codecs
import argparse

def decode_tags(data):
    repls = [',','\\','\n',' ', '\r\n', '\r']
    pattern = r'<(\d+)>(.*?)<\/\1>'    
    tags = re.findall(pattern, data, re.DOTALL)
    decoded_tags = []
    for tag_id, hex_data in tags:
        hex_data = reduce(lambda a, v: a.replace(v,''), repls, hex_data)
        decoded_data = binascii.unhexlify(hex_data)
        decoded_data = codecs.decode(decoded_data, 'cp1251')
        decoded_tags.append(f'<{tag_id}>\n{decoded_data}</{tag_id}>')


    gr_pattern = r'<gr-id>(.*?)</gr-id>'    
    gr_data = re.findall(gr_pattern, data, re.DOTALL)
    hex_data = reduce(lambda a, v: a.replace(v,''), repls, gr_data[0])
    gr_data = binascii.unhexlify(hex_data)
    gr_data = codecs.decode(gr_data, 'cp1251')

    return decoded_tags, gr_data

def process_questions(xml_data):
    repls = ['\n','\r\n', '\r']
    question_blocks = re.findall(r'<\d+>.*?</\d+>', xml_data, re.DOTALL)
    questions_dict = {}

    for question_block in question_blocks:
        question_id = re.search(r'<(\d+)>', question_block).group(1)

        question = re.search(r'<question>(.*?)</question>', question_block, re.DOTALL).group(1).strip()
        question = reduce(lambda a, v: a.replace(v,''), repls, question)
        question_data = {
            'question': question,
            'type': int(re.search(r'type=(\d+)', question_block).group(1)),
            'right': int(re.search(r'right=(\d+)', question_block).group(1)),
        }

        answers = re.findall(r'<a_\d+>(.*?)</a_\d+>', question_block, re.DOTALL)
        question_data['answers'] = [answer.strip() for answer in answers]

        questions_dict[question_id] = question_data

    return questions_dict


def process_group_list(gr_data):
    gr_out = {}

    gr_list = re.search(r'<GR-List>(.*?)</GR-List>', gr_data, re.DOTALL)
    if gr_list:
        gr_list_content = gr_list.group(1).strip()
        gr_list_array = gr_list_content.split('\n')
        gr_out['GR-List'] = [s.replace('\r', '') for s in gr_list_array]

    gr_tags = re.findall(r'<GR-(\d+)>(.*?)</GR-(\d+)>', gr_data, re.DOTALL)
    for gr_tag in gr_tags:
        gr_number = gr_tag[0]
        gr_content = gr_tag[1].strip()
        tv_d = re.search(r'<tv_d>(.*?)</tv_d>', gr_content, re.DOTALL)

        if tv_d:
            tv_d_content = tv_d.group(1).strip()
            tv_d_array = tv_d_content.split('\n')
            gr_out[gr_number] = [s.replace('\r', '') for s in tv_d_array]
    
    return gr_out


def main():
    parser = argparse.ArgumentParser(description='Decode FDB file')
    parser.add_argument('fdb_file', type=str, help='Input FDB file')
    parser.add_argument('html_file', type=str, help='Output html file')
    args = parser.parse_args()

    with open(args.fdb_file, 'r', encoding='cp1251') as f:
        fdb_data = f.read()

    decoded_tags, gr_data = decode_tags(fdb_data)
    xml_data = "\n".join(decoded_tags)

    questions = process_questions(xml_data)
    gr_data = process_group_list(gr_data)

    grouped_questions = {}

    for group_id, group_name in enumerate(gr_data['GR-List']):
        group_data = {
            'group_name': group_name,
            'questions': []
        }

        question_ids = gr_data.get(str(group_id), [])

        for question_id in question_ids:
            question_data = questions.get(question_id)
            if question_data:
                group_data['questions'].append(question_data)

        grouped_questions[str(group_id)] = group_data



    #print(json.loads(json.dumps(grouped_questions)))
    html_content = generate_html(grouped_questions)

    with open(args.html_file, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)


js_text = '''
<script>
document.querySelector("button").addEventListener("click", (e) => {
    if (e.target.innerText === "Enable test mode") {
        const style = document.createElement("style");
        style.textContent = "answers{visibility:hidden;}question:hover+answers{visibility:visible;}";
        document.head.appendChild(style);
        e.target.innerText = "Disable test mode";
    } else {
        document.head.removeChild(document.head.querySelector("style"));
        e.target.innerText = "Enable test mode";
    }
});
</script>

<script>
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.display === "block") {
      content.style.display = "none";
    } else {
      content.style.display = "block";
    }
  });
}
</script>
'''

css_text = '''
<style>
.collapsible {
  background-color: #eee;
  color: #444;
  cursor: pointer;
  padding: 18px;
  width: 100%;
  border: none;
  text-align: left;
  outline: none;
  font-size: 15px;
}
.active, .collapsible:hover {
  background-color: #ccc;
}
.content {
  padding: 0 18px;
  display: none;
  overflow: hidden;
  background-color: #f1f1f1;
}
</style>
'''


def generate_html(grouped_questions):
    html_page = '<html><head><title>Test</title></head><body>'
    html_page += css_text
    html_page += '<button>Enable test mode</button><br><br>'

    for group_id, group_data in grouped_questions.items():
        #html_page += f'<h1>{group_data["group_name"]}</h1>'
        html_page += f"<button type='button' class='collapsible'><h2>{group_data['group_name']}</h2></button>"
        html_page += "<div class='content'>"
        html_page += '<ol>'
        for question in group_data['questions']:
            html_page += '<hr>'
            html_page += '<li>'
            html_page += f'<question type={question["type"]}><p>{question["question"]}</p></question>'
            html_page += '<answers>'
            html_page += f'<ul>'
            
            if question["type"] == 1:
                answers = question["answers"]
                for i, answer in enumerate(answers):
                    if i < question["right"]:
                        html_page += f'<li><strong>{answer}</strong></li>'
                    else:
                        html_page += f'<li>{answer}</li>'
            
            elif question["type"] == 2:
                answers = question["answers"]
                for i, answer in enumerate(answers):
                    if i < question["right"]:
                        html_page += f'<li><strong>{answer}</strong></li>'
                    else:
                        html_page += f'<li>{answer}</li>'
            
            elif question["type"] == 3:
                answers = question["answers"]
                for i, answer in enumerate(answers):
                    html_page += f'<li><strong>{i + 1}. {answer}</strong></li>'
            
            elif question["type"] == 6:
                answers = question["answers"]
                for answer in answers:
                    html_page += f'<li><strong>{answer}</strong></li>'
            
            elif question["type"] == 7:
                answers = question["answers"]
                for answer in answers:
                    html_page += f'<li><strong>{answer}</strong></li>'

            html_page += '</ul>'
            html_page += '</answers>'
            html_page += '</li>'

        html_page += '</ol>'
        html_page += '</div>'
    
    html_page += js_text
    html_page += '</body></html>'
    return html_page

            
if __name__ == "__main__":
    main()
