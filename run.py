from asyncio import tasks
from glob import glob
from tkinter import ALL
from typing import Protocol
from matplotlib.pyplot import draw_if_interactive
import requests
import time
import sys  
import pickle
import os
import modules
from modules import citing_tree, reference_tree
from tool import all_cited_set, all_reference_set, load
from tool import href2doi, get_all_references, get_cited_list, get_all_cited_nodes, get_all_reference_nodes
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from time import sleep
from tqdm import tqdms

ALL_NODES_DICT = {} # doi : node 
DOI2TITLE = {}  # doi(str) : title of article (str) [unprocessed]
ROOT_URL = 'https://pubmed.ncbi.nlm.nih.gov/'
ROOT_DOI = '34265844'
MAX_URL_LIMIT = 7 # 每次最大爬取子文献的上限，日如果是比较浅的树，建议设置得大一些
TOTAL_DOC_LIMIT = 400   # 一共爬取的有效节点数量
REFERENCE_COUNT = 0
TOTAL_DOC_COUNT = 0

REFERENCE_DIRECTORY = './reference/'
CITED_DIRECTORY = './cited/'
REFERENCE_ALL_NODES_DICT_PATH = REFERENCE_DIRECTORY + 'reference_all_nodes_dict.pickle'
REFERENCE_DOI2TITLE_PATH = REFERENCE_DIRECTORY + 'reference_doi2title.pickle'
REFERENCE_TREE_PATH = REFERENCE_DIRECTORY + 'reference_tree.pickle'
CITED_ALL_NODES_DICT_PATH = CITED_DIRECTORY + 'cited_all_nodes_dict.pickle'
CITED_DOI2TITLE_PATH = CITED_DIRECTORY + 'cited_doi2title.pickle'
CITED_TREE_PATH = CITED_DIRECTORY + 'cited_tree.pickle'
DRIVER_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chromedriver.exe'

task = 'crawl_cited_paper'
driver = webdriver.Chrome(DRIVER_PATH)

if task == 'crawl_cited_paper':
    get_all_cited_nodes(driver, ROOT_URL+ROOT_DOI, ALL_NODES_DICT, DOI2TITLE, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH, ROOT_URL, TOTAL_DOC_LIMIT,)
elif task == 'crawl_reference_paper':
    get_all_reference_nodes(driver, ROOT_URL, ALL_NODES_DICT, DOI2TITLE, REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, TOTAL_DOC_LIMIT, MAX_URL_LIMIT)
elif task == 'build_cited_tree':
    load('citing', REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH)
    root_node = ALL_NODES_DICT[ROOT_DOI]
    cited_tree = citing_tree(root_node, ALL_NODES_DICT, DOI2TITLE)
    pickle.dump(cited_tree, open(CITED_TREE_PATH, 'wb'), protocol=3)
elif task == 'build_reference_tree':
    load('reference', REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH)
    root_node = ALL_NODES_DICT[ROOT_DOI]
    ref_tree = reference_tree(root_node, ALL_NODES_DICT, DOI2TITLE)
    pickle.dump(ref_tree, open(REFERENCE_TREE_PATH, 'wb'), protocol=3)
elif task == 'output_all_reference_doc_by_stack_num':
    load('reference', REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH)
    ref_tree = pickle.load(open(REFERENCE_TREE_PATH, 'rb'))
    max_stack_num = max( [node.stack_num for node in ALL_NODES_DICT.values()] )
    for num in range(0, max_stack_num+1):
        crnt_set = all_reference_set(ref_tree, num, ALL_NODES_DICT, DOI2TITLE)
        with open(REFERENCE_DIRECTORY + str(num) + '.txt', 'w', encoding='utf-8') as fout:
            for title in crnt_set:
                fout.write(crnt_set)
elif task == 'output_all_citing_doc_by_stack_num':
    load('citing', REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH)
    cited_tree = pickle.load(open(CITED_TREE_PATH, 'rb'))
    max_stack_num = max( [node.stack_num for node in ALL_NODES_DICT.values()] )
    for num in range(0, max_stack_num+1):
        crnt_set = all_cited_set(cited_tree, num, ALL_NODES_DICT, DOI2TITLE)
        with open(CITED_DIRECTORY + str(num) + '.txt', 'w', encoding='utf-8') as fout:
            for title in crnt_set:
                fout.write(crnt_set)