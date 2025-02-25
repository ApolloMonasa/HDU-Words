import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import pdfplumber
import re
import os
from openai import OpenAI

# 全局变量
count = 0

# 读取键盘输入并赋值给interval
def get_user_input():
    print("请选择模式：")
    print("1. 测试")
    print("2. 考试")
    mode = int(input("请输入模式编号（1或2）："))
    print("请输入做题间隔时间(单位为秒)：")
    interval = float(input())
    print("请输入做题总数：")
    total = int(input())
    print(f"本次时间间隔为：{interval}s，预期答题时间：{interval * total + 60}s")
    return mode, interval, total

# 设置DataBase
def extract_text_from_pdf(pdf_path, start_page, end_page):
    text_list = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            if end_page is not None and page_number > end_page:
                break
            if page_number >= start_page:
                text = page.extract_text()
                if text:
                    text_list.append(text)
    return text_list

def parse_text_to_dict(text_list):
    word_dict = {}
    pattern = re.compile(r'(\b\w+\b)\s+(.*)')
    for text in text_list:
        lines = text.splitlines()
        for line in lines:
            match = pattern.match(line)
            if match:
                word = match.group(1)
                meaning = match.group(2).strip()
                word_dict[word] = meaning
    return word_dict

def parse_text_to_dict_NI(text_list):
    word_dict = {}
    pattern = re.compile(r'(\b\w+\b)\s+(.*)')
    for text in text_list:
        lines = text.splitlines()
        for line in lines:
            match = pattern.match(line)
            if match:
                meaning = match.group(2)
                word = match.group(1).strip()
                word_dict[word] = meaning
    return word_dict

# 初始化浏览器
def init_browser():
    mobile_emulation = {
        "deviceMetrics": {
            "width": 1707,
            "height": 773,
            "pixelRatio": 1.0
        },
        "userAgent": "Mozilla/5.0 (Linux; Android 13; IQOO 18) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    }
    chrome_options = Options()
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    wd = webdriver.Chrome(service=Service(r"./chromedriver.exe"), options=chrome_options)
    return wd

# 开始测试或考试
def start_test_or_exam(wd, interval, total, mode):
    global count
    for i in range(total):
        question = WebDriverWait(wd, 15, 0.5).until(
            lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[2]/div/div[1]/span[2]'))
        question = question.text.split()[0].strip()
        A = WebDriverWait(wd, 15, 0.1).until(lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/div/div[1]/div[1]/span'))
        B = WebDriverWait(wd, 15, 0.1).until(lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/div/div[2]/div[1]/span'))
        C = WebDriverWait(wd, 15, 0.1).until(lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/div/div[3]/div[1]/span'))
        D = WebDriverWait(wd, 15, 0.1).until(lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]/div/div[4]/div[1]/span'))
        At = A.text.split('.')[1].strip()
        Bt = B.text.split('.')[1].strip()
        Ct = C.text.split('.')[1].strip()
        Dt = D.text.split('.')[1].strip()
        con = f"""{question}\nA.{At}\nB.{Bt}\nC.{Ct}\nD.{Dt}"""
        print(con)
        if question.isalpha():
            flag = 1
            for word, meaning in word_dict.items():
                if question == word:
                    if At in meaning and Bt not in meaning and Ct not in meaning and Dt not in meaning:
                        flag = 0
                        A.click()
                        break
                    if Bt in meaning and At not in meaning and Ct not in meaning and Dt not in meaning:
                        flag = 0
                        B.click()
                        break
                    if Ct in meaning and Bt not in meaning and At not in meaning and Dt not in meaning:
                        flag = 0
                        C.click()
                        break
                    if Dt in meaning and Bt not in meaning and Ct not in meaning and At not in meaning:
                        flag = 0
                        D.click()
                        break
            if flag:
                count += 1
                client = OpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com"
                )
                completion = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {'role': 'system', 'content': '你要做的是词义匹配，找到和英文单词最贴切的中文解释，最终回答一个用"-"包起来的大写字母作为答案,例如"-B-"'},
                        {'role': 'user', 'content': con},
                    ]
                )
                WebDriverWait(wd, 10, 0.1).until(lambda wd: '-' in completion.choices[0].message.content)
                print(f"-----(英译中){i + 1}  " + completion.choices[0].message.content)
                if '-A-' in completion.choices[0].message.content:
                    A.click()
                if '-B-' in completion.choices[0].message.content:
                    B.click()
                if '-C-' in completion.choices[0].message.content:
                    C.click()
                if '-D-' in completion.choices[0].message.content:
                    D.click()
                completion.choices[0].message.content = None
        else:
            flag = 1
            for word, meaning in word_dict_NI.items():
                if question in word:
                    if At in meaning:
                        flag = 0
                        A.click()
                        break
                    if Bt in meaning:
                        flag = 0
                        B.click()
                        break
                    if Ct in meaning:
                        flag = 0
                        C.click()
                        break
                    if Dt in meaning:
                        flag = 0
                        D.click()
                        break
            if flag:
                count += 1
                client = OpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com"
                )
                completion = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {'role': 'system', 'content': '你要做的是词义匹配，找到和中文意思最贴切的英语单词，最终回答一个用"-"包起来的大写字母作为答案,例如"-B-"'},
                        {'role': 'user', 'content': con},
                    ]
                )
                WebDriverWait(wd, 10, 0.1).until(lambda wd: '-' in completion.choices[0].message.content)
                print(f"-----(中译英){i + 1}  " + completion.choices[0].message.content)
                if '-A-' in completion.choices[0].message.content:
                    A.click()
                if '-B-' in completion.choices[0].message.content:
                    B.click()
                if '-C-' in completion.choices[0].message.content:
                    C.click()
                if '-D-' in completion.choices[0].message.content:
                    D.click()
                completion.choices[0].message.content = None
        time.sleep(interval)
    time.sleep(0.1)
    if mode == 2:  # 如果是考试模式，提交答案
        wd.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/div/div[3]/span').click()
        time.sleep(0.1)
        wd.find_element(By.XPATH, '/html/body/div[4]/div[2]/button[2]').click()
    print(f"使用了{count}次AI")
    time.sleep(999999)

# 主函数
def main():
    mode, interval, total = get_user_input()
    print("Database Setting>>>.....")
    pdf_path = r'./Data.pdf'
    start_page = 1
    end_page = 113
    text_list = extract_text_from_pdf(pdf_path, start_page, end_page)
    global word_dict, word_dict_NI
    word_dict = parse_text_to_dict(text_list)
    word_dict_NI = parse_text_to_dict_NI(text_list)
    for word, meaning in word_dict.items():
        print(f"{word}=={meaning}")
    for word, meaning in word_dict_NI.items():
        print(f"{word}=={meaning}")
    print("Task Beginning>>>.....")
    wd = init_browser()
    wd.get("https://skl.hduhelp.com/?type=5#/english/list")
    wd.maximize_window()
    time.sleep(2.5)
    began = WebDriverWait(wd, 150, 0.1).until(lambda wd: wd.find_element(By.XPATH, '//*[@id="app"]/div/div[3]/div/div[2]/div[2]/div/button'))
    began.click()
    start_test_or_exam(wd, interval, total, mode)

if __name__ == "__main__":
    main()