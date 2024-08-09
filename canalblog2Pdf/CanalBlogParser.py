import urllib.parse
import requests
import urllib
import json
import time
import re
import os

from documents import Article, Commentaire
from genericpath import exists
from bs4 import BeautifulSoup
from datetime import datetime
from dateparser import parse

class CanalBlogParser():
    def __init__(self) -> None:
        self.base_url: str = "http://yojik.canalblog.com"
        self.query_after = "\n query LoadMoreComments(\n $after: String!,\n $locale: Locale!\n $postID: ID!,\n ){\n comments(\n after: $after,\n locale: $locale\n postID: $postID,\n ) {\n edges {\n node {\n \n id\n date\n comment\n popularity\n user {\n isAuthor\n avatar\n name\n website\n }\n\n replies {\n edges {\n node {\n \n id\n date\n comment\n popularity\n user {\n isAuthor\n avatar\n name\n website\n }\n\n }\n }\n pageInfo {\n endCursor\n hasNextPage\n }\n }\n }\n }\n pageInfo {\n endCursor\n hasNextPage\n }\n }\n }\n"

    def __sort_folders_by_year(self, folder: dict) -> int:
        """ Trie les dossiers par date."""
        return folder['year']

    def __get_folders_by_date(self) -> list[dict]:
        """ Récupères les dossiers contenant les articles par leurs années de créations."""

        folders: list[dict] = []

        # URL vers le sommaire
        url: str = urllib.parse.urljoin(self.base_url, "/summary")

        # Requête vers le sommaire
        req: requests.Response = requests.get(url)
        if req.status_code != 200:
            print(f"{url} - HTPP {req.status_code}")
            return folders
        soup: BeautifulSoup = BeautifulSoup(req.content, "html5lib")
        time.sleep(1)
        req.close()

        # Récupères la liste des articles
        summary_archives_list = soup.find("ul", {"id": "summary_archives_list"})
        if not summary_archives_list:
            print(f"{url} - summary_archives_list is None")
            return folders

        # Parcours les dossiers contenant les articles
        summary_archives_year_list: list[BeautifulSoup] = summary_archives_list.find_all(
            "li", {"class": "summary_archives_year-list"})
        for summary_archive in summary_archives_year_list:

            year = int(summary_archive.get("data-year"))
            urls: list[str] = []
            for url in summary_archive.find_all("a"):
                urls.append(urllib.parse.urljoin(self.base_url, url.get('href')))

            folders.append({"year": year, "urls": urls})

        return folders


    def __get_articles_by_page(self, url: str) -> list[Article]:
        """ Récupères les articles depuis une page"""
        
        articles: list[Article] = []

        # REQUETE HTTP
        req: requests.Response = requests.get(url)
        if req.status_code != 200:
            print(f"{url} - HTPP {req.status_code}")
            return articles
        soup: BeautifulSoup = BeautifulSoup(req.content, "html5lib")
        time.sleep(1)
        req.close()

        # Récupères les liens des articles
        article_links: list[BeautifulSoup] = soup.find_all(
            "a", {"class": "article_link"})
        for link in article_links:
            
            # Analyse les articles pour récupérer les métadonnées
            article: Article = self.parse_article(
                urllib.parse.urljoin(self.base_url, link.get("href")))
            if not article:
                continue
            articles.append(article)

        return articles

    def __get_comments_by_article(self, article_id: str, after: str = None, comments: list[Commentaire] = None) -> list[Commentaire]:
        """ Récupères les commentaires d'un article à partir d'un ID. """

        url: str = urllib.parse.urljoin(self.base_url, "/comments/graphql")
        data: dict = {
            "query": "\n query RootComments(\n $locale: Locale!\n $postID: ID!,\n ){\n viewer {\n name\n email\n avatar\n blogs {\n edges {\n node {\n id,\n url,\n name\n }\n }\n pageInfo {\n endCursor\n hasNextPage\n }\n }\n }\n comments(\n locale: $locale\n postID: $postID,\n ) {\n recaptchaPublicKey\n commentsOverblogAllowed\n commentsOverblogAllowedVotes\n edges {\n node {\n \n id\n date\n comment\n popularity\n user {\n isAuthor\n avatar\n name\n website\n }\n\n replies {\n edges {\n node {\n \n id\n date\n comment\n popularity\n user {\n isAuthor\n avatar\n name\n website\n }\n\n }\n }\n pageInfo {\n endCursor\n hasNextPage\n }\n }\n }\n }\n pageInfo {\n endCursor\n hasNextPage\n }\n }\n }\n",
            "variables": {
                "locale": "fr",
                "postID": article_id
            }
        }

        if after:
            data["variables"]['after'] = after
            data['query'] = self.query_after

        # REQUETE HTTP POST
        req: requests.Response = requests.post(url, data=json.dumps(data), headers={
                                            "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"})
        if req.status_code != 200:
            print(f"{url} - HTPP {req.status_code}")
            return comments
        response: dict = json.loads(req.content)
        time.sleep(1)
        req.close()
        
        # Récupères le contenu de la réponse
        response_data: dict = response['data']
        comments_data: dict = response_data.get('comments')
        if not comments_data:
            return comments_data

        # Si il y a pas d'edges il y a pas de commentaires
        edges: list[dict] = comments_data.get('edges')
        if not edges:
            return comments

        if comments is None:
            comments:list[Commentaire] = list()

        # Parcours les commentaires
        for edge in edges:
            commentaire = Commentaire()

            commentaire.content = edge['node']['comment']
            commentaire.auteur = edge['node']['user']['name']

            commentaire.date = datetime.strptime(
                edge['node']['date'], "%d/%m/%Y %H:%M")

            commentaire.id = edge['node']['id']
            
            comments.append(commentaire)

        if comments_data['pageInfo']['endCursor'] is None or comments_data['pageInfo']['endCursor'] == after:
            return comments

        return self.__get_comments_by_article(article_id=article_id, after=comments_data['pageInfo']['endCursor'], comments=comments)


    def parse_article(self, url: str) -> Article:
        
        # REQUETE HTTP GET
        req: requests.Response = requests.get(url)
        if req.status_code != 200:
            print(f"{url} - HTPP {req.status_code}")
            return None
        soup: BeautifulSoup = BeautifulSoup(req.content, "html5lib")
        time.sleep(1)
        req.close()

        # Récupères le contenu
        content = soup.find("div", {"class": "content"})
        if content is None:
            return None

        # Analyse la page pour obtenir l'article
        article = Article()

        # Récupères le titre, la date et le corps de l'article
        article.date = parse(content.find(
            "div", {"class": "date-header"}).text.strip(), languages=['fr'])
        article.title = content.find(
            "h2", {"class": "single-content_title"}).text.strip()
        article.body = content.find(
            "div", {"class": "single-content_content"}).prettify()

        # Récupères les catégories de l'article
        tags: list[BeautifulSoup] = content.find_all(
            "span", {"class": "article_footer_tag"})
        for tag in tags:
            article.categorie.append(tag)

        # Récupères les commentaires de l'articles
        post_comments = soup.find("div",{"class":"post-comments"})
        script_comment = post_comments.find("script")
        if script_comment:
            
            # Récupères l'ID de l'article dans le script
            script_text = script_comment.next.replace("\n","").replace("\t"," ").strip()
            article_id = re.search(
                    r'(?:.*?postID.*?)(\d{1,}).*', script_text)
            article.id = article_id.group(1).strip()
            
            # Récupères les commentaires à partir d'un appel HTTP
            if article_id:
                article.commentaires = self.__get_comments_by_article(article_id=article.id)
                
        return article


    def __save_articles_on_folers(self, year: int, articles: list[Article]) -> None:

        path_folder: str = f"output/{year}"
        if not exists(f"output/{year}"):
            os.mkdir(path_folder)

        for article in articles:
            file_name = f"{article.date.strftime('%d-%m-%Y')}_{article.title.replace(' ','_').strip()}.json"

            file = open(f"{path_folder}/{file_name}", "w+")
            file.write(article.to_json())
            file.close()
            print(f"\"{file_name}\" sauvegardé.")
    
    def start(self) -> None:

        folders: list[dict] = self.__get_folders_by_date()
        if len(folders) < 1:
            exit()

        nbs_articles:int = 0
        folders.sort(key=self.__sort_folders_by_year)
        for folder in folders:
            urls: list[str] = folder['urls']
            for url in urls:
                articles: list[Article] = self.__get_articles_by_page(url)
                self.__save_articles_on_folers(year=folder['year'], articles=articles)
                nbs_articles += len(articles)
        print(f"{nbs_articles} articles récupéré(s)")
