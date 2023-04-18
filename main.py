import json
import re
import signal
import sys
import texttable
from termcolor import colored
import datetime
import sqlite3
from time import strftime, localtime
import matplotlib.pyplot as plt
import numpy as np

USER_ID = 1


def main():
    insert_sql = ''' insert into vocab_history (date, chapter, test_paper, accuracy, mistake) values (?,?,?,?,?) '''
    insert_mistake_vocab_sql = ''' insert into mistake_vocab_history (vocab_history_id, vocab, user_id) values (?,?,?) '''
    vocab, v_list = init_vocabulary()
    signal.signal(signal.SIGINT, end)
    signal.signal(signal.SIGTERM, end)
    # draw list number
    list_chapter = texttable.Texttable()
    chapter_headers = ["id", "content"]
    list_chapter.add_row(chapter_headers)
    list_chapter.set_cols_align(["l", "l"])
    list_chapter.set_cols_valign(["m", "m"])
    for v in v_list:
        list_chapter.add_row([str(v), v_list[v]])
    print(list_chapter.draw())
    try:
        user_choose = input('select the chapter you want to test:')
        if int(user_choose) < 0 or int(user_choose) > len(v_list):
            print('test is not exist')
            return
    except ValueError:
        print('only input digits will be accepted')
        return

    c, t = v_list[int(user_choose)].split('-')
    cc = int(re.findall(r'\d', c)[0])
    tt = int(re.findall(r'\d', t)[0])
    headers = ["id", "origin", "tester", "correct"]
    table = texttable.Texttable()
    table.add_row(headers)
    table.set_cols_align(["l", "l", "l", "l"])
    table.set_cols_valign(["m", "m", "m", "m"])

    mistake_vocab = []
    total_words = 0
    correct = 0
    error = 0
    i = 1
    for word in vocab[c][t]:
        total_words = len(vocab[c][t])
        text = colored("word " + str(i) + ":", "green")
        v = input(text)
        word_lower = word.lower()
        if v == word_lower:
            correct = correct + 1
        else:
            error = error + 1
            mistake_vocab.append(word_lower)

        cor = "✅" if v == word_lower else "❌"
        row = [i, word_lower, v, cor]
        table.add_row(row)
        i = i + 1

    print(table.draw())
    accuracy = round(correct / total_words, 4)
    print("✅准确率:", accuracy * 100, "%")
    print("❌错误个数:", error)
    date = strftime('%Y-%m-%d %H:%M:%S', localtime())

    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    sql_data = (date, cc, tt, accuracy * 10000, error)
    res = c.execute(insert_sql, sql_data)
    insert_mistake_vocab_sql_data = (res.lastrowid, json.dumps(mistake_vocab), USER_ID)

    if len(mistake_vocab) != 0:
        c.execute(insert_mistake_vocab_sql, insert_mistake_vocab_sql_data)

    conn.commit()

    draw7days(v_list[int(user_choose)])
    count_wrong_vocab_percentage(v_list[int(user_choose)])
    conn.close()


def draw7days(user_choose):
    d = get_user_vocab_history(user_choose)
    # x轴是时间(月份+日子)
    x = []

    # y轴1是准确率
    y1 = []

    # y轴2是错误数字
    y2 = []

    for row in d:
        date = row[1]
        md = date.split()[0].split("-", 1)[1]
        hm = date.split()[1].split(":")
        x.append(md + " " + hm[0] + ":" + hm[1])
        accuracy = row[4]
        y1.append(accuracy / 100)
        mistake = row[5]
        y2.append(mistake)

    fig, ax = plt.subplots(figsize=(7, 3), dpi=200)

    # --- Remove spines and add gridlines
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(ls="--", lw=0.5, color="#4E616C")

    ax.plot(x, y2, marker="o", mfc="white", ms=5)
    ax.plot(x, y1, marker="o", mfc="white", ms=5)

    ax.xaxis.set_tick_params(length=2, color="#4E616C", labelcolor="#4E616C", labelsize=6)
    ax.yaxis.set_tick_params(length=2, color="#4E616C", labelcolor="#4E616C", labelsize=6)

    plt.legend(['mistake', 'accuracy'])
    plt.title(user_choose)
    # 绘制 准确率的数字
    for x1, y1 in zip(x, y1):
        plt.text(x1, y1 + 1, str(y1), ha='center', va='bottom', fontsize=6, rotation=0)

    for x1, y2 in zip(x, y2):
        plt.text(x1, y2 + 1, str(y2), ha='center', va='bottom', fontsize=6, rotation=0)
    # 绘制 错误字数的数字

    plt.show()


def count_wrong_vocab_percentage(user_choose):
    colors = ["#A0CBE8", "#F28E2B", "#FFBE7D", "#59A14F", "#8CD17D", "#B6992D", "#F1CE63", "#499894",
              "#86BCB6", "#E15759", "#E19D9A"]
    d = get_user_vocab_history(user_choose)
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    ids = []
    mistake_vocab = {}
    for row in d:
        ids.append(row[0])

    res = c.execute('select * from mistake_vocab_history where vocab_history_id in (%s) ' % ','.join('?' * len(ids)),
                    ids)

    for row in res:
        vocab = json.loads(row[2])
        for v in vocab:
            if v not in mistake_vocab.keys():
                mistake_vocab[v] = 1
            else:
                mistake_vocab[v] = mistake_vocab[v] + 1

    if len(mistake_vocab) == 0:
        return

    sorted_vocab = sorted(mistake_vocab, reverse=True)
    num_list = []
    for sv in sorted_vocab:
        num_list.append(mistake_vocab[sv])
    fig, ax = plt.subplots(figsize=(7, 3), dpi=200)
    # --- Remove spines and add gridlines
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_tick_params(length=2, color="#4E616C", labelcolor="#4E616C", labelsize=6)

    ax.set_xticks([])
    x = np.arange(len(num_list))

    for i, j in zip(num_list, x):
        plt.text(i + 0.05, j, '%.0f' % i, ha='center', va='bottom', fontsize=6)

    plt.barh(sorted_vocab, num_list, color=colors)
    plt.title(user_choose, fontsize=8)
    plt.show()


def load_vocabulary_file():
    f = open('vocabulary.json')
    return json.load(f)


def get_user_vocab_history(user_choose):
    c, t = user_choose.split('-')
    cc = int(re.findall(r'\d', c)[0])
    tt = int(re.findall(r'\d', t)[0])
    today = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=+1), '%Y-%m-%d')
    sub7days = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=-7), '%Y-%m-%d')
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    d = c.execute("select * from vocab_history where chapter = ? and test_paper = ? and date between ? and ?",
                  (cc, tt, sub7days, today))
    return d


def init_vocabulary():
    vocab = {}
    vocab_list = {}
    i = 1
    vocabulary = load_vocabulary_file()
    for chapter in vocabulary:
        for tests in vocabulary[chapter]:
            if chapter not in vocab:
                vocab[chapter] = {}
            for test in tests:
                vocab[chapter][test] = tests[test]
                vocab_list[i] = chapter + '-' + test
                i = i + 1

    return vocab, vocab_list


def end(signum, frame):
    print("\nend")
    sys.exit()


if __name__ == '__main__':
    main()
    # draw7days('chater3-test1')
    # count_wrong_vocab_percentage('charter3-test2')
