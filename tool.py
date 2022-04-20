from glob import glob
import time
import sys  
import pickle
import os
from tkinter import ALL

from psutil import getloadavg
from modules import citing_tree, reference_node, reference_tree
from modules import citing_node
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from time import sleep
from tqdm import tqdm

TOTAL_DOC_COUNT = 0
CITED_COUNT = 0
print(TOTAL_DOC_COUNT)

def href2doi(href_list):
    doi_list = [href[10:].strip('/') for href in href_list]
    doi_list = [href[max(href.rfind('pmc')+3, href.rfind('/')+1):] for href in doi_list]
    return doi_list

def get_all_references(driver:WebDriver,DOI2TITLE):
    try:
        button = driver.find_element(by=By.XPATH, value='//*[@id="top-references-list"]/div/div/button')   # click button to release all references
        button.click()
        print('reference button clicked')
    except:
        return None, None
    time.sleep(1)   # wait for the web to load new references //*[@id="top-references-list-1"]/li[1]/ol/li/a[3]
    attemps = 0
    while attemps < 2:
        try:
            references_href_raw_a = driver.find_elements(by=By.XPATH, value='//*[@id="top-references-list-1"]/li/ol/li/a')
            references_href_raw_a = [a for a in references_href_raw_a if a.text == 'PubMed']
            references_href = [a.get_attribute('href') for a in references_href_raw_a]
            references_doi = href2doi(references_href)    
            references_raw_li = driver.find_elements(by=By.XPATH, value='//*[@id="top-references-list-1"]/li//li')
            references = [e.text for e in references_raw_li]
            for (doi, title) in zip(references_doi, references):    # update DOI2DOC
                DOI2TITLE[doi] = title 
            break 
        except:
            attemps += 1
            driver.refresh()
            sleep(0.5)
    if attemps == 2:
        print('$$$$  ERROR  $$$$  reference page can\'t get')
        sys.exit(TimeoutError)
    return references_doi, references_href

def get_all_reference_nodes(driver:WebDriver, url, ALL_NODES_DICT, DOI2TITLE, REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, TOTAL_DOC_LIMIT, MAX_URL_LIMIT, MAX_RECURSING_DEPTH, crnt_stack_num=0, father_title=None):
    if crnt_stack_num == 0:
        global CITED_COUNT
        CITED_COUNT = 0
    if abs(crnt_stack_num) > MAX_RECURSING_DEPTH:
        return
    url_attemps = 0
    while url_attemps < 2:
        try:
            driver.get(url) # enter new doc
            break
        except:
            url_attemps += 1
            continue
    if url_attemps >= 2:
        print("\n%%%%%  capturing timeout url  %%%%%", url, '\n')
        return 
    
    print('entering new doc')
    paper_title = None
    paper_doi = href2doi([url])[0]
    authors = None   
    # print('current ALL_NODE_DICT keys: ', ALL_NODES_DICT.keys())
    try:
        paper_title_h = driver.find_element(by=By.XPATH, value='//*[@id="full-view-heading"]/h1')
        paper_title = paper_title_h.text.strip()
        if paper_doi in ALL_NODES_DICT:
            print('repeated document : ', paper_title)
            ALL_NODES_DICT[paper_doi].doc.add_new_father(father_title)
            return 
        author_raw_span = driver.find_elements(by=By.XPATH, value='//*[@id="full-view-heading"]/div[2]/div/div/span')
        authors = [span.text.strip('1234567890#, ') for span in author_raw_span]
    except:
        print('invalid document url')
        return 
    print('current document: ', paper_title)
    references_doi, references_href = get_all_references(driver)
    if references_doi == None and references_href == None:
        print('current url reference information unavailable, can\'t open: ', url)
        return 
    print('got references', 'length of references doi: ', len(references_doi), 'length of references href: ', len(references_href))
    
    crnt_node = reference_node(references_href, references_doi, paper_doi, paper_title, authors, father_title, crnt_stack_num, url)
    ALL_NODES_DICT[paper_doi] = crnt_node
    print(paper_title, ' constructed!')
    if crnt_stack_num != 0:
        global TOTAL_DOC_COUNT
    TOTAL_DOC_COUNT += 1
    if TOTAL_DOC_COUNT % 5 == 0:
        print('\n*****', TOTAL_DOC_COUNT, ' nodes have been successfully created!*****\n')
    if TOTAL_DOC_COUNT % 20 == 0:
        pickle.dump(ALL_NODES_DICT, open(REFERENCE_ALL_NODES_DICT_PATH + str(TOTAL_DOC_COUNT) + '_all_nodes_dict.pickle', 'wb'), protocol=3)
        pickle.dump(DOI2TITLE, open(REFERENCE_DOI2TITLE_PATH + str(TOTAL_DOC_COUNT) + '_doi2title.pickle', 'wb'), protocol=3)
        print('\nwriting pickles\n')
    print('current stack depth: ', crnt_stack_num)
    # sleep(1)  # 反 反爬虫

    local_doc_count = 0
    for href in references_href:
        if local_doc_count >= MAX_URL_LIMIT:
            print('reaching local reference limit   returning......')
            break
        if TOTAL_DOC_COUNT >= TOTAL_DOC_LIMIT:
            print('reaching global reference limit   returning......')
            break
        out = get_all_reference_nodes(driver, href, ALL_NODES_DICT, DOI2TITLE, REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, TOTAL_DOC_LIMIT, MAX_URL_LIMIT, MAX_RECURSING_DEPTH, crnt_stack_num+1, paper_title)
        if out:
            local_doc_count += 1
    if crnt_stack_num == 0:
        print('all reference nodes have been created')
    return paper_title


def get_cited_list(main_page_url, DRIVER_PATH, ROOT_URL, DOI2TITLE):
    driver = webdriver.Chrome(DRIVER_PATH)
    url = main_page_url if 'http' in main_page_url else ROOT_URL + main_page_url
    driver.get(url)
    total_page_num = driver.find_element(by=By.XPATH, value='//*[@id="search-results"]/div[2]/div[2]/div/label[2]').text
    total_page_num = int(total_page_num[total_page_num.find(' ')+1:])
    cited_herf = []
    cited_doi = []
    for i in tqdm(range(total_page_num), desc='citing pages: ', file=sys.stdout):
        raw_a_list = driver.find_elements(by=By.XPATH, value='//*[@id="search-results"]/section/div[1]/div/article/div[2]/div[1]/a')
        # print('length of raw_a_list: ', len(raw_a_list))
        crnt_page_cited = [a.text for a in raw_a_list]
        crnt_page_cited_href = [a.get_attribute('href') for a in raw_a_list]
        crnt_page_cited_doi = href2doi(crnt_page_cited_href)

        for (doi, title) in zip(crnt_page_cited_doi, crnt_page_cited):  # update DOI2DOC
            DOI2TITLE[doi] = title
        cited_herf.extend(crnt_page_cited_href) # append crnt cited docs into total cited docs
        cited_doi.extend(crnt_page_cited_doi)

        button = driver.find_element(by=By.XPATH, value='//*[@id="search-results"]/div[2]/div[2]/button[3]') # enter the next page of citing pages
        if i+1 < total_page_num:
            button.click()
    driver.quit()
    return cited_doi[1:], cited_herf[1:] # 这个cited_paper里面第一个是原文

def get_all_cited_nodes(driver:WebDriver, url, ALL_NODES_DICT, DOI2TITLE, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH, ROOT_URL, TOTAL_DOC_LIMIT, crnt_stack_num=0, father_title=None):
    if crnt_stack_num == 0:
        global TOTAL_DOC_COUNT
        global CITED_COUNT
        CITED_COUNT = 0
        TOTAL_DOC_COUNT = 0
    if abs(crnt_stack_num) > 4:
        return
    url_attemps = 0
    while url_attemps < 2:
        try:
            driver.get(url) # enter new doc
            break
        except:
            continue
    if url_attemps >= 2:
        print("\n%%%%%  capturing timeout url  %%%%%", url, '\n')
        return 
    
    print('entering new doc')
    paper_title = None
    paper_doi = href2doi([url])[0]
    authors = None   
    # print('current ALL_NODE_DICT keys: ', ALL_NODES_DICT.keys())
    try:
        paper_title_h = driver.find_element(by=By.XPATH, value='//*[@id="full-view-heading"]/h1')
        paper_title = paper_title_h.text.strip()
        if paper_doi in ALL_NODES_DICT:
            print('repeated document : ', paper_title)
            ALL_NODES_DICT[paper_doi].doc.add_new_father(father_title)
            return 
        author_raw_span = driver.find_elements(by=By.XPATH, value='//*[@id="full-view-heading"]/div[2]/div/div/span')
        authors = [span.text.strip('1234567890#, ') for span in author_raw_span]
    except:
        print('invalid document url')
        return 
    print('current document: ', paper_title)
        
    cited_page_url = None
    cited_href = []
    cited_doi = []
    try:
        cited_page_url = driver.find_element(by=By.XPATH, value='//*[@id="citedby"]/div/a').get_attribute('data-href')
        cited_page_url = cited_page_url if 'http' in cited_page_url else ROOT_URL + cited_page_url
    except:
        pass
    if cited_page_url:
        cite_attemps = 0
        while cite_attemps < 2:
            try:
                cited_doi, cited_href = get_cited_list(cited_page_url)
                break
            except:
                cite_attemps += 1
        if cite_attemps >= 2:
            print('$$$$  ERROR  $$$$  cite page can\'t get')
        print('got cited')
    else:
        print('no cited')
        return 

    crnt_node = citing_node(cited_href, cited_doi, paper_title, paper_doi, authors, father_title, crnt_stack_num, url)
    ALL_NODES_DICT[paper_doi] = crnt_node
    print(paper_title, ' constructed!')
    if crnt_stack_num != 0:
        print(crnt_stack_num)
        # global TOTAL_DOC_COUNT
    TOTAL_DOC_COUNT += 1
    if TOTAL_DOC_COUNT % 5 == 0:
        print('\n*****', TOTAL_DOC_COUNT, ' nodes have been successfully created!*****\n')
    if TOTAL_DOC_COUNT % 20 == 0:
        pickle.dump(ALL_NODES_DICT, open(CITED_ALL_NODES_DICT_PATH + str(TOTAL_DOC_COUNT) + '_all_nodes_dict.pickle', 'wb'), protocol=3)
        pickle.dump(DOI2TITLE, open(CITED_DOI2TITLE_PATH + str(TOTAL_DOC_COUNT) + '_doi2title.pickle', 'wb'), protocol=3)
        print('\nwriting pickles\n')
    print('current stack depth: ', crnt_stack_num)
    # sleep(1)  # 反 反爬虫
    # if crnt_stack_num != 0:
    #     global CITED_COUNT
    # local_count = 0
    for href in cited_href:
        # if local_count >= MAX_HREF_LIMIT:
        #     print('reaching local reference limit   returning......')
        #     break
        if CITED_COUNT >= TOTAL_DOC_LIMIT:
            print('reaching citing doc limit   returning......')
            break
        out = get_all_cited_nodes(driver, href, ALL_NODES_DICT, DOI2TITLE, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH, ROOT_URL, TOTAL_DOC_LIMIT, crnt_stack_num+1, paper_title)
        # if out:
        #     local_count += 1
    if crnt_stack_num == 0:
        print('all nodes have been created')
    return paper_title

def all_reference_set(tree:reference_tree, stack_num, ALL_NODES_DICT, DOI2TITLE):
    all_title = set()
    if stack_num == 0:
        for doi in tree.root.reference_node.doc.references_doi:
            all_title |= {ALL_NODES_DICT[doi]}
        return all_title
    for children in tree.all_nodes_bottom_up_generator():
        for child in children:
            if child.reference_node.stack_num == stack_num:
                for doi in child.reference_node.references_doi:
                    all_title |= {DOI2TITLE[doi]}
    return all_title

def all_cited_set(tree:citing_tree, stack_num, ALL_NODES_DICT, DOI2TITLE):
    all_title = set()
    if stack_num == 0:
        for doi in tree.root.citing_node.doc.citing_doi:
            all_title |= {ALL_NODES_DICT[doi]}
        return all_title
    for children in tree.all_nodes_bottom_up_generator():
        for child in children:
            if child.citing_node.stack_num == stack_num:
                for doi in child.citing_node.citing_doi:
                    all_title |= {DOI2TITLE[doi]}
    return all_title


def load(type:str, REFERENCE_ALL_NODES_DICT_PATH, REFERENCE_DOI2TITLE_PATH, CITED_ALL_NODES_DICT_PATH, CITED_DOI2TITLE_PATH):
    ALL_NODES_DICT = {}
    DOI2TITLE = {}
    if type == 'reference':
        try:
            ALL_NODES_DICT = pickle.load( open(REFERENCE_ALL_NODES_DICT_PATH, 'rb') )
        except:
            print('----------- ERROR ALL_NODES_DICT HAVEN\'T BEEN BUILT -------------')
            raise(NameError('variable not built'))
        try:
            DOI2TITLE = pickle.load( open(REFERENCE_DOI2TITLE_PATH, 'rb') )
        except:
            print('----------- ERROR DOI2TITLE HAVEN\'T BEEN BUILT -------------')
            raise(NameError('variable not built'))
    elif type == 'citing':
        try:
            ALL_NODES_DICT = pickle.load( open(CITED_ALL_NODES_DICT_PATH, 'rb') )
        except:
            print('----------- ERROR ALL_NODES_DICT HAVEN\'T BEEN BUILT -------------')
            raise(NameError('variable not built'))
        try:
            DOI2TITLE = pickle.load( open(CITED_DOI2TITLE_PATH, 'rb') )
        except:
            print('----------- ERROR DOI2TITLE HAVEN\'T BEEN BUILT -------------')
            raise(NameError('variable not built'))
    else:
        raise(KeyError('invalid input in load function'))
    return ALL_NODES_DICT, DOI2TITLE