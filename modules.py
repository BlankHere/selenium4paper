import requests
import time
import sys  
import pickle
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from time import sleep
from tqdm import tqdm


##################################################################
## all classes needed for reference paper crawling & processing ##
##################################################################
class reference_doc:
    def __init__(self, references_url:list=None, references_doi:list=None, paper_title:str=None, paper_doi=None, authors:list=None, father_paper_title:str=None, url:str=None) -> None:
        self.references_url = references_url  # 该文献引用文献的 url 访问链接
        self.references_doi = references_doi  # 该文献引用文献对应的 doi 号
        self.authors = authors  # 作者
        self.paper_title = paper_title  # 标题
        self.father_paper_titles = [father_paper_title] # 父节点
        self.main_page_url = url    # 该文献的访问链接
        self.doi = paper_doi    # 该文献的 doi 号
    def add_new_father(self, paper_title):
        self.father_paper_titles.append(paper_title)

class reference_node:
    def __init__(self, reference_url:list=None, references_doi:list=None, paper_title:str=None, paper_doi=None, authors:list=None, father_paper_title:str=None, stack_num=None, url:str=None):
        self.doc = reference_doc(reference_url, references_doi, paper_doi, paper_title, authors, father_paper_title, url)
        self.stack_num = stack_num # 是第几层找到的

class reference_tree_node:
    def __init__(self, node:reference_node):
        self.reference_node = node
        self.children = []

class reference_tree:
    def __init__(self, root_node:reference_tree_node, ALL_NODES_DICT, DOI2TITLE):
        self.all_nodes = []
        self.ALL_NODES_DICT = ALL_NODES_DICT
        self.DOI2TITLE = DOI2TITLE
        self.temp_doi_list = list(ALL_NODES_DICT.keys())
        self.temp_parse_list = []
        self.root = self.build_tree(reference_tree_node(root_node))

    def build_tree(self, crnt_node:reference_tree_node):
        crnt_references_doi = crnt_node.reference_node.doc.references_doi
        crnt_doi = crnt_node.reference_node.doc.doi
        self.temp_doi_list.remove(crnt_doi)
        for doi in crnt_references_doi:
            if doi not in self.temp_doi_list:
                continue
            child_node = reference_tree_node(self.ALL_NODES_DICT[doi])
            crnt_node.children.append(self.build_tree(child_node))
        self.all_nodes.append(crnt_node)
        return crnt_node

    def parse_tree(self, target_stack_depth, crnt_node:reference_tree_node=None):
        if crnt_node == None:
            crnt_node = self.root
            self.temp_parse_list = []
        if target_stack_depth == crnt_node.reference_node.stack_num:
            self.temp_parse_list.append(crnt_node.reference_node.doc.paper_title)
        for child in crnt_node.children:
            if child.reference_node.stack_num <= target_stack_depth:
                self.parse_tree(target_stack_depth, child)
        return self.temp_parse_list
                

    def all_nodes_bottom_up_generator(self, crnt_node:reference_tree_node=None):
        if crnt_node == None:
            crnt_node = self.root
        for child in crnt_node.children:
            if len(child.children) > 0:
                for children in self.all_nodes_bottom_up_generator(child):
                    yield children
        yield crnt_node.children

    def all_paper_bottom_up_generator(self, crnt_node:reference_tree_node=None):        
        if crnt_node == None:
            self.temp_all_doi_list = list(self.DOI2TITLE.keys())
            crnt_node = self.root
        for children in self.all_nodes_bottom_up_generator():
            for child in children:
                child_reference_papers_doi = child.reference_node.doc.references_doi
                for doi in child_reference_papers_doi:
                    if doi in self.temp_all_doi_list:
                        self.temp_all_doi_list.remove(doi)
                    else:
                        child_reference_papers_doi.remove(doi)
                yield child_reference_papers_doi        

    def search_for_reference_doi(self, doi):  # search for an exact node corresponding to a doi
        pass

    def search_for_reference_doc(self, doi):    # search in reference_doi list, may not be an exact node
        pass


##############################################################
## all classes needed for cited paper crawling & processing ##
##############################################################
class citing_doc:
    def __init__(self, citing_href:list=None, citing_doi:list=None, paper_title:str=None, paper_doi=None, authors:list=None, father_paper_title:str=None, url:str=None) -> None:
        self.citing_href = citing_href
        self.citing_doi = citing_doi
        self.authors = authors
        self.paper_title = paper_title
        self.father_paper_titles = [father_paper_title]
        self.main_page_url = url
        self.doi = paper_doi
    def add_new_father(self, paper_title):
        self.father_paper_titles.append(paper_title)

class citing_node:
    def __init__(self, citing_href:list=None, citing_doi:list=None, paper_title:str=None, paper_doi=None, authors:list=None, father_paper_title:str=None, stack_num=None, url:str=None):
        self.doc = citing_doc(citing_href, citing_doi, paper_doi, paper_title, authors, father_paper_title, url)
        self.stack_num = stack_num # 是第几层找到的

class citing_tree_node:
    def __init__(self, node:citing_node):
        self.citing_node = node
        self.children = []

class citing_tree:
    def __init__(self, root_node:citing_tree_node, ALL_NODES_DICT, DOI2TITLE):
        self.temp_parse_list = []
        self.ALL_NODES_DICT = ALL_NODES_DICT
        self.DOI2TITLE = DOI2TITLE
        self.temp_doi_list = list(ALL_NODES_DICT.keys())
        self.temp_all_doi_list = list(DOI2TITLE.keys())
        self.root = self.build_tree(citing_tree_node(root_node))

    def build_tree(self, crnt_node:citing_tree_node):
        crnt_citing_doi = crnt_node.citing_node.doc.citing_doi
        crnt_doi = crnt_node.citing_node.doc.doi
        self.temp_doi_list.remove(crnt_doi)
        for doi in crnt_citing_doi:
            if doi not in self.temp_doi_list:
                continue
            child_node = citing_tree_node(self.ALL_NODES_DICT[doi])
            crnt_node.children.append(self.build_tree(child_node))
        return crnt_node

    def parse_tree(self, target_stack_depth, crnt_node:citing_tree_node=None):
        if crnt_node == None:
            crnt_node = self.root
            self.temp_parse_list = []
        if target_stack_depth == 0:
            self.temp_parse_list.append(crnt_node.citing_node.doc.paper_title)
            return self.temp_parse_list
        if target_stack_depth-1 == crnt_node.citing_node.stack_num:
            print('&')
            self.temp_parse_list.extend([self.DOI2TITLE[doi] for doi in crnt_node.citing_node.doc.citing_doi])
        for child in crnt_node.children:
            print(child.citing_node.stack_num)
            if child.citing_node.stack_num < target_stack_depth-1:
                self.parse_tree(target_stack_depth, child)
        return self.temp_parse_list
    
    def all_nodes_bottom_up_generator(self, crnt_node:citing_tree_node=None):
        if crnt_node == None:
            crnt_node = self.root
        for child in crnt_node.children:
            if len(child.children) > 0:
                for children in self.all_nodes_bottom_up_generator(child):
                    yield children
        yield crnt_node.children

    def all_paper_bottom_up_generator(self, crnt_node:citing_tree_node=None):        
        if crnt_node == None:
            self.temp_all_doi_list = list(self.DOI2TITLE.keys())
            crnt_node = self.root
        for children in self.all_nodes_bottom_up_generator():
            for child in children:
                child_citing_papers_doi = child.citing_node.doc.citing_doi
                for doi in child_citing_papers_doi:
                    if doi in self.temp_all_doi_list:
                        self.temp_all_doi_list.remove(doi)
                    else:
                        child_citing_papers_doi.remove(doi)
                yield child_citing_papers_doi

    def search_for_citing_doi(self, doi):  # search for an exact node corresponding to a doi
        pass

    def search_for_citing_doc(self, doi):    # search in citing_doi list, may not be an exact node
        pass