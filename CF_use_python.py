# coding: utf-8 -*-
import math
import pandas as pd


class UserCf:
    # 这个类的主要功能是提供一个基于用户的协同过滤算法
    
    def __init__(self):
        """初始化文件路径，读取书籍评分数据集"""
        self.file_path = './data/BX-Book-Ratings.csv'
        self._init_frame()

    def _init_frame(self):
        self.frame = pd.read_csv(self.file_path,sep=None, error_bad_lines=False)
        self.frame.columns=['UserID','BookID','Rating'] 

    @staticmethod
    def _cosine_sim(target_books, books):

        union_len = len(set(target_books) & set(books))
        if union_len == 0: return 0.0
        product = len(target_books) * len(books)
        cosine = union_len / math.sqrt(product)
        return cosine

    def _get_top_n_users(self, target_user_id, top_n):
        """
        计算和当前用户最相似的top_n (此时top_n为10) 个用户
        :param target_user_id:当前计算的用户ID
        :param top_n: 需要计算的相似的用户数
        :return: 和当前用户最相似的top_n个用户
        """
        # 当前用户评价过的书籍列表
        target_books = self.frame[self.frame['UserID'] == target_user_id]['BookID']
        # 除去当前用户后的用户列表
        other_users_id = [i for i in set(self.frame['UserID']) if i != target_user_id]
        # 其他用户评价的书籍的集合
        other_books = [self.frame[self.frame['UserID'] == i]['BookID'] for i in other_users_id]

        # _cosine_sim()函数计算当前用户评分过的书籍target_books和其他用户评分过的书籍的余弦相似度，此相似度即为用户相似度
        sim_list = [self._cosine_sim(target_books, books) for books in other_books]
        # 将余弦相似度和userID通过zip函数组合起来并排序
        sim_list = sorted(zip(other_users_id, sim_list), key=lambda x: x[1], reverse=True)
        return sim_list[:top_n]

    def _get_candidates_items(self, target_user_id):
        """
        找出当前用户没有评分的所有书籍
        Find all books in source data and target_user did not meet before.
        """
        # 当前用户评价过的BookID
        target_user_books = set(self.frame[self.frame['UserID'] == target_user_id]['BookID'])
        # 当前用户未评价过的BookID
        other_user_books = set(self.frame[self.frame['UserID'] != target_user_id]['BookID'])
        # 不同时包含于target_user_books和other_user_books的元素
        candidates_books = list(target_user_books ^ other_user_books)
        return candidates_books

    def _get_top_n_items(self, top_n_users, candidates_books, top_n):
        """
            本函数用于计算给当前用户推荐度最高的top_n本书
        """
        # 选取出当前用户最相似的top_n个用户的数据
        top_n_user_data = [self.frame[self.frame['UserID'] == k] for k, _ in top_n_users]
        interest_list = []
        # 遍历当前用户为评分的书籍以及和当前用户最相似的top_n个用户
        for book_id in candidates_books:
            tmp = []
            for user_data in top_n_user_data:
                # 如果遍历的用户对当前书籍评分过，则取出当前对book_id的评分并取平均值；如果未评分，则置为0
                if book_id in user_data['BookID'].values:
                    readdf = user_data[user_data['BookID'] == book_id]
                    tmp.append(round(readdf['Rating'].mean(), 2))
                else:
                    tmp.append(0)
            # 计算top_n个用户对当前书籍的评分值与余弦相似度的乘积，并将其相加，作为当前书籍的兴趣值
            interest = sum([top_n_users[i][1] * tmp[i] for i in range(len(top_n_users))])
            # 将最终所得值和book_id关联，作为目标用户对当前书籍的感兴趣值
            interest_list.append((book_id, interest))
        # 按照兴趣值的从高到底进行排序
        interest_list = sorted(interest_list, key=lambda x: x[1], reverse=True)
        return interest_list[:top_n]

    def calculate(self, target_user_id, top_n):
        """
        基于用户的协同过滤
        :param target_user_id:用户编号
        :param top_n:推荐的书籍本数量
        :return:给当前用户推荐的书籍BookID以该书籍的评分score
        """
        # 计算和当前用户最相似的top_n个用户
        top_n_users = self._get_top_n_users(target_user_id, top_n)
        # 计算当前用户没有评分的所有书籍
        candidates_books = self._get_candidates_items(target_user_id)
        # 计算当前用户最感兴趣的10本书
        top_n_books = self._get_top_n_items(top_n_users, candidates_books, top_n)
        
        print(top_n_books)
        name = []
        values = []
        # 遍历推荐书籍列表，将其格式化为UserID、BookID和score形式
        for x in top_n_books:
            name.append(x[0])
            values.append(x[1])
        df = pd.DataFrame({'UserID': target_user_id, 'BookID': name, 'score': values})
        return df


def run(i):
    """
    run函数可以进行多线程的计算，调用calculate函数计算单个user的书籍推荐表DF，计算完成后将DF合并到res中
    :param i: 用户编号
    """
    # 全局的res
    global res
    target_user_id = users[i]
    DF = usercf.calculate(target_user_id, top_n)
    res = res.append(DF)
    

import random
# 读取书籍评分数据，数据的三列分别是UserID, BookID, Rating
path = './data/BX-Book-Ratings.csv'
Data = pd.read_csv(path, sep=None, error_bad_lines=False)
Data.columns = ['UserID', 'BookID', 'Rating']
# 创建用于存储最终结果的DataFrame
res = pd.DataFrame(columns=['UserID', 'BookID', 'score'])
# 初始化User类，在初始化时，会调用其__init__(self)方法
usercf = UserCf()

# 随机的选取20次,set是不重复元素的集合
users = [random.choice(list(set(Data['UserID']))) for x in range(20)]
# 推荐10本书
top_n = 10
# 根据随机选取的20个用的编号，开启20个线程开始计算推荐的书籍
for x in range(len(users)):
    print(x)
    run(x)
    print(res)
# 将计算完全的数据输出为文件
res.to_csv('./data/booktuijian.csv', index=False)
