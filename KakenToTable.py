import xmltodict
import pandas as pd
import json
import re
import numpy as np
from tqdm import tqdm
from pathlib import Path

class KakenToTable():

  def __init__(self, kaken_xml_path):
    '''
    kaken_xml(str):xmlファイルのパス
    '''

    with open(kaken_xml_path, "r")as f:
      str_data = f.read()
    raw_data = xmltodict.parse(str_data)

    self.kaken_lst = raw_data['grantAwards']['grantAward']

  def repmenber_info2(self, ja_members, lst=True):

    #日本語がリスト
    if lst:
      team = 1
      #代表者
      rep_member = ja_members[0]
      #研究者番号
      erad_number = rep_member.get("@eradCode")
      #所属機関
      institution = rep_member.get("institution")
      #所属学部
      department = rep_member.get("department")
      #ポスト名
      jobTitle = rep_member.get("jobTitle")
      #名前
      name_exist = rep_member.get("personalName")
      ##名前が存在するか
      if name_exist:
        fullName = name_exist.get("fullName") if type(name_exist)!=list else name_exist[0]["fullName"]

      else:
        fullName = None

    #日本語がdict
    else:

      team = 0
      #代表者
      rep_member = ja_members
      #研究者番号
      erad_number = rep_member.get("@eradCode")
      #所属機関
      institution = rep_member.get("institution")
      #所属学部
      department = rep_member.get("department")
      #ポスト名
      jobTitle = rep_member.get("jobTitle")
      #名前
      name_exist = rep_member.get("personalName")
      ##名前が存在するか
      if name_exist:
        fullName = name_exist.get("fullName") if type(name_exist)!=list else name_exist[0]["fullName"]

      else:
        fullName = None


    return team, erad_number, institution, department, jobTitle, fullName

  def reseacher_info(self, kaken_dict):

    #前提：日本語のは基本ある(1万件/1万件)
    ja_members = kaken_dict["summary"][0]["member"]
    en_members = kaken_dict["summary"][1].get("member")
    #海外との協力か
    foreign_colab = 0

    #1英語がある場合
    if en_members:
      ##1.1英語がdictのとき
      if isinstance(en_members, dict):
        ###1.1.1日本語がdictのとき
        if isinstance(ja_members, dict):
          ###基本は日本語で、名前だけ英語を参照

          team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=False)
          all_members = [self.making_dict(ja_members)]


        ###1.1.2日本語がlistのとき
        else:
          ###日本語のsequenceのリストja_sequences_lstを作る
          ja_sequence_lst = [member['@sequence'] for member in ja_members]
          en_sequence = en_members["@sequence"]

          ####1.1.2.1 en_dictのsequenceがja_sequences_lstに入っている
          if en_sequence in ja_sequence_lst:
            target = en_sequence  #日英で共通していたsequence
            # index:targetとなるsequenceを持つ辞書が、ja_members(リスト)においてどの位置にあるか
            # dic:index:targetとなるsequenceを持つ辞書が、ja_members(リスト)においてどの位置にあるか
            index, target_dic = next((i, d) for i, d in enumerate(ja_members) if d.get("@sequence") == target)

            #####1.1.2.1.1 共通していたsequenceは日本語版においてPersonalNameキーを持っていたのか
            #####もっていたら、ただの日英翻訳なので問題ない
            if target_dic.get("personalName"):
              #代表者
              team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
              all_members = [self.making_dict(member) for member in ja_members]

            #####もっていなかったら、日本語版の海外研究者の名前抜けていて、それが英語版にあるということなので補う
            else:

              ja_members[index]["personalName"] = {
                  "fullName": en_members.get("personalName",{}).get("fullName")
              }

              #代表者
              team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
              #その他のメンバー
              #日本の辞書リストで統一されている
              all_members = [self.making_dict(member) for member in ja_members]
              foreign_colab = 1



          ####1.1.2.2 en_dictのsequenceがja_sequences_lstに入っていない
          else:
              # sequenceが日本語側に存在しない → 英語メンバーを追加
              if en_sequence == "1":
                  ja_members.insert(0, en_members)  # 代表者は先頭に
              else:
                  ja_members.append(en_members)

              team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
              all_members = [self.making_dict(member) for member in ja_members]
              foreign_colab = 1




      ##1.2英語がlistのとき
      else:
        ###1.2.1日本語がdictのとき
        if isinstance(ja_members, dict):

          ja_members = [ja_members]
          ja_seq_to_idx = {member["@sequence"]: i for i, member in enumerate(ja_members)} #リストにしてやる
          en_seq_to_idx = {member["@sequence"]: i for i, member in enumerate(en_members)}

          ja_seq_set = set(ja_seq_to_idx)
          en_seq_set = set(en_seq_to_idx)


          # 英語にしかいない @sequence の要素を ja_members に追加
          diff = en_seq_set - ja_seq_set

          if diff:
            foreign_colab=1

          for seq in diff:
              en_member = en_members[en_seq_to_idx[seq]]
              if seq == "1":
                  ja_members.insert(0, en_member)
              else:
                  ja_members.append(en_member)

          # 共通する sequence で、日本語のほうにpersonalName がないものには補完
          for seq in ja_seq_set & en_seq_set:
              ja_index = ja_seq_to_idx[seq]
              ja_member = ja_members[ja_index]

              #personalNameがない
              if "personalName" not in ja_member:
                  en_member = en_members[en_seq_to_idx[seq]]
                  ja_member["personalName"] = {
                      "fullName": en_member.get("personalName", {}).get("fullName", "")
                  }
                  foreign_colab=1

          team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
          all_members = [self.making_dict(member) for member in ja_members]



        ###1.2.2日本語がlistのとき
        else:
          # "@sequence → index へのマッピング辞書

          ja_seq_to_idx = {member["@sequence"]: i for i, member in enumerate(ja_members)}
          en_seq_to_idx = {member["@sequence"]: i for i, member in enumerate(en_members)}

          ja_seq_set = set(ja_seq_to_idx)
          en_seq_set = set(en_seq_to_idx)

          # 英語にしかいない @sequence の要素を ja_members に追加
          diff = en_seq_set - ja_seq_set
          if diff:
            foreign_colab=1

          for seq in diff:
              en_member = en_members[en_seq_to_idx[seq]]
              if seq == "1":
                  ja_members.insert(0, en_member)
              else:
                  ja_members.append(en_member)

          # 共通する sequence で、日本語のほうにpersonalName がないものには補完
          for seq in ja_seq_set & en_seq_set:
              ja_index = ja_seq_to_idx[seq]
              ja_member = ja_members[ja_index]

              #personalNameがない
              if "personalName" not in ja_member:
                  en_member = en_members[en_seq_to_idx[seq]]
                  ja_member["personalName"] = {
                      "fullName": en_member.get("personalName", {}).get("fullName", "")
                  }
                  foreign_colab=1

          team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
          all_members = [self.making_dict(member) for member in ja_members]


    #2英語がない場合
    else:
      ##2.1日本語がdictのとき
        if isinstance(ja_members, dict):
          team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=False)
          all_members = [self.making_dict(ja_members)]

      ##2.2日本語がlistのとき
        else:
          team, erad_number, institution, department, jobTitle, fullName = self.repmenber_info2(ja_members, lst=True)
          all_members = [self.making_dict(member) for member in ja_members]



    return team, foreign_colab, erad_number, institution, department, jobTitle, fullName, all_members

  def making_dict(self, member, lst=True):

    men_dict = {
    "@eradCode": member.get("@eradCode"),
    "institution": member.get("institution"),
    "department": member.get("department"),
    "jobTitle": member.get("jobTitle"),
      }
    #名前
    name_exist = member.get("personalName")
      ##名前が存在するか

    if name_exist:
      fullName = name_exist.get("fullName") if type(name_exist)!=list else name_exist[0]["fullName"]

    else:
      fullName = None

    men_dict["fullName"] = fullName

    return men_dict

  def kaken_to_table(self, kaken_dict):


    #awardNumber
    number = kaken_dict.get("@awardNumber")
    #作成日
    date = kaken_dict.get('created')

    #url
    url = kaken_dict["urlList"]["url"]

    #値がある方だけ返す。両方値がある場合は、前の値を返す
    title = kaken_dict["summary"][0].get("title") or kaken_dict["summary"][1].get("title")

    #研究種目(基盤研究Bや'国際共同研究加速基金)
    shumoku = kaken_dict["summary"][0].get("category",{}).get('#text')

    #研究分野(2019年以前)
    #　A>史学>アメリカ史みたいになっているので、最後の小区分だけとってきている
    if kaken_dict["summary"][0].get("field"):
      if type(kaken_dict["summary"][0]["field"]) == list:
        field = kaken_dict["summary"][0]["field"][-1]["#text"]
      else:
        field = kaken_dict["summary"][0].get("field",{}).get("#text")
    else:
        field = None


    #審査区分(2019年以降)
    kubun = kaken_dict["summary"][0].get("review_section")
    if kubun:
      if type(kubun) == list:
        goudou = 1
        sinsa_kubun = [k["#text"] for k in kaken_dict["summary"][0]["review_section"]]


      else:
        goudou = 0
        sinsa_kubun = [kaken_dict["summary"][0]["review_section"]["#text"]]


    else:
      goudou = 0
      sinsa_kubun = []

    #研究機関

    if kaken_dict["summary"][0].get("institution"):
      if isinstance(kaken_dict["summary"][0]["institution"], list):
        base_institution = [inst["#text"] for inst in kaken_dict["summary"][0]["institution"]]
      else:
        base_institution = [kaken_dict["summary"][0]["institution"]["#text"]]

    #記載がない場合は代表メンバーの所属機関を持ってくる
    else:
      if isinstance(kaken_dict["summary"][0]["member"], list):
        base_institution = [kaken_dict["summary"][0]["member"][0].get("institution")]
      else:
        base_institution = [kaken_dict["summary"][0]["member"].get("institution")]


    #研究者の情報

    team, foreign_colab, erad_number, institution, department, jobTitle, fullName, all_members = self.reseacher_info(kaken_dict)


    #交付中(adopted)・完了(project_closed)
    if kaken_dict["summary"][0].get("projectStatus"):
      state_=kaken_dict["summary"][0]["projectStatus"]
      state = state_['@statusCode']
    else:
      state = None

    #たまにキーワードが一つの人がその場合はlistにならないみたい
    if kaken_dict["summary"][0].get("keywordList"):

      if type(kaken_dict["summary"][0]["keywordList"]["keyword"]) == list:
        keywords = [dic["#text"] for dic in kaken_dict["summary"][0]["keywordList"]["keyword"]]
      else:
        keywords = [kaken_dict["summary"][0]['keywordList']['keyword']["#text"]]

    else:
      keywords = []

    #研究開始時の概要
    #'paragraphListは、ない・ひとつ・リストの場合がある
    # 2019-:研究開始時の研究の概要 @type': outline_of_research_initial
    # 1974-2012:研究概要 '@type': 'abstract
    # 2013-:研究実績の概要  '@type': 'outline_of_research_performanc'
    # 2016-:研究成果の学術的意義や社会的意義 significance_of_research_achievement
    # @sequence1:現在までの達成度'@type': 'progress
    # @sequence1:今後の研究の推進方策：planning_scheme

    paragraphList = kaken_dict["summary"][0].get("paragraphList")

    #ここで辞書を作っておく
    paragraph_dict = {
        'outline_of_research_initial': "",
        'outline_of_research_performance': "",
        'abstract': "",
        'outline_of_research_achievement': "",
        'significance_of_research_achievement':"",
        'progress': "",
        'planning_scheme':"",
        'plan_of_carry_over':"",
        'planning_budget_expenditure':"",

    }


    #説明文が存在する
    if paragraphList:
      #リストになっている(outline_of_research_performancやprogressなど)
      if type(paragraphList) == list:

        for para in paragraphList:
          kind = para['@type'] # outline_of_research_performancやprogress
          texts = para['paragraph'] # それぞれの説明文

          if type(texts) == list: #説明文がさらにリストになっている場合がある
            for text in texts:
              paragraph_dict[kind] += text['#text']

          #例：s2["summary"][0][3]['paragraph']
          else:
            paragraph_dict[kind] += texts['#text']


      #例:s12
      else:
        kind = paragraphList['@type']
        texts = paragraphList['paragraph']
        if type(texts) == list: #listの場合がある
            for text in texts:
              paragraph_dict[kind] += text['#text']

        else:
            paragraph_dict[kind] += texts['#text']




    # 交付開始-交付修了
    if kaken_dict["summary"][0]['periodOfAward'].get('startDate'):
      start_date = kaken_dict["summary"][0]['periodOfAward']['startDate']
    else:
      start_date = None

    if kaken_dict["summary"][0]['periodOfAward'].get('endtDate'):
      end_date = kaken_dict["summary"][0]['periodOfAward']['endDate']['#text']

    else:
      end_date = None

    #交付金
    if kaken_dict["summary"][0].get("overallAwardAmount"):
      money = int(kaken_dict["summary"][0]["overallAwardAmount"]["totalCost"])
    else:
      money = None

    #ここからkeyがsummaryではなくなる

    #['reportList'] 実績
    #['productList'] 成果物
    productList = kaken_dict.get('productList')
    #正規表現のパターン
    pattern = r"[・、,，]"

    if productList :

        product_list = []

        if type(productList['product']) == list:

            for pro in productList['product']:

              #proは各プロダクト

              #pro["@type"]は以下の5種類からなる(はず)
              #journal_article
              #book
              #presentation
              #symposium
              #jointInternational
              pro_type = pro["@type"]
              #出版日(発行日)

              if "year" in pro:
                if isinstance(pro["year"], dict):
                  pro_year = int(pro["year"]["#text"])
                else:
                  pro_year = int(pro["year"]) #たまに{"year":{"#text":n}}ではなく{"year":n}}
              else:
                pro_year = None

              #.splitを使っているから著者名(発表者)1人でもリストになる
              #.replace("\u3000", " ")で全角スペースを半角に変換もしている
              if pro.get("author"):
                if type(pro["author"]) == dict:
                  pro_author = re.split(pattern, pro["author"]["#text"].replace("\u3000", " "))

                else:
                  pro_author = re.split(pattern, pro["author"].replace("\u3000", " "))

              else:
                pro_author = []


              #タイトル
              pro_title = pro.get("title")
              #ジャーナル名
              pro_journal = pro.get("journalTitle")
              #presentationの団体
              pro_organizer = pro.get('organizer')
              #査読付きか(ジャーナルの場合のみ)
              pro_reviewed = pro.get("reviewed")
              #招待かどうか
              pro_invited = pro.get("invited")

              pro_dict={
              "type":pro_type,
              "year":pro_year,
              "author":pro_author,
              "title":pro_title,
              "journal":pro_journal,
              "organizer":pro_organizer,
              "reviewed":pro_reviewed,
              "invited": pro_invited
              }

              product_list.append(pro_dict)

        else:
              pro_type = productList['product']["@type"]

              if "year" in productList['product']:
                if isinstance(productList['product']["year"], dict):
                  pro_year = int(productList['product']["year"]["#text"])
                else:
                  pro_year = int(productList['product']["year"])

              else:
                pro_year = None


              #著者名(発表者)1人でもリストになる
              #全角スペースを半角に変換もしている
              if productList['product'].get("author"):
                if type(productList['product']["author"]) == dict:
                  pro_author = re.split(pattern, productList['product']["author"]["#text"].replace("\u3000", " "))

                else:
                  pro_author = re.split(pattern, productList['product']["author"].replace("\u3000", " "))

              else:
                pro_author = []

              #タイトル
              pro_title = productList['product'].get("title")
              #ジャーナル名
              pro_journal = productList['product'].get("journalTitle")
              #presentationの団体
              pro_organizer = productList['product'].get('organizer')
              #査読付きか(ジャーナルの場合のみ)
              pro_reviewed = productList['product'].get("reviewed")
              #招待かどうか
              pro_invited = productList['product'].get("invited")

              pro_dict={
              "type":pro_type,
              "year":pro_year,
              "author":pro_author,
              "title":pro_title,
              "journal":pro_journal,
              "organizer":pro_organizer,
              "reviewed":pro_reviewed,
              "invited": pro_invited
              }

              product_list.append(pro_dict)

    else:
      product_list = []




    res_dict = {
      "awardNumber":number,
      "date":date,
      "url":url,
      "title":title,
      "shumoku":shumoku,
      "field":field,
      "goudou":goudou,
      "sinsa_kubun":sinsa_kubun,
      "base_institution":base_institution,
      "team":team,
      "foreign_colab":foreign_colab,
      "erad_number":erad_number,
      "institution":institution,
      "department":department,
      "jobTitle":jobTitle,
      "fullName":fullName,
      "all_members": all_members,
      "state":state,
      "keywords":keywords,
      "start_date":start_date,
      "end_date":end_date,
      "money":money,
      "product_list":product_list

    }

    res_dict.update(paragraph_dict)

    return res_dict

  def to_json(self, save_path = None, save=False):
    dict_list = [self.kaken_to_table(self.kaken_lst[i]) for i in tqdm(range(len(self.kaken_lst)))]
    if save:
        save_path = Path(save_path)
        with save_path.open('w', encoding='utf-8') as f:
          json.dump(dict_list, f, ensure_ascii=False, indent=2)
    
    return dict_list

  def to_pd(self):
    return pd.DataFrame( [self.kaken_to_table(self.kaken_lst[i]) for i in tqdm(range(len(self.kaken_lst)))])



