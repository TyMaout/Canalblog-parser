import time
import locale
import logging
import requests

from datetime import datetime
from copy import deepcopy
from bs4 import BeautifulSoup
from documents import Article, Commentaire
from weasyprint import HTML

logging.basicConfig(
    format="%(asctime)s : %(levelname)-8s {%(module)s} {%(filename)s:%(lineno)d} : %(message)s")
logger = logging.getLogger('weasyprint')
logger = logging.getLogger('weasyprint.progress')

locale.setlocale(locale.LC_TIME, '')


class Article2Pdf():
    def __init__(self) -> None:

        # Charge le modèle pour les pages du PDF
        template: str = open("templates/template_column.html", "+r").read()
        self.soup: BeautifulSoup = BeautifulSoup(template, 'html.parser')

        template_comment: str = open(
            "templates/template_comment.html", "+r").read()
        self.soup_comment: BeautifulSoup = BeautifulSoup(
            template_comment, 'html.parser')

    def __check_img(self, url: str) -> str:
        """ Vérifie si l'image est bien chargée."""
        try:
            req = requests.get(url)
            if req.status_code != 200:
                return False
            return True
        except Exception as e:
            print(e)
            return False

    def __check_contenu_article(self, content: BeautifulSoup) -> BeautifulSoup:

        # Trouves les images dans le contenu et vérifie si elles sont chargés
        for img in content.find_all("img"):
            img: BeautifulSoup
            if self.__check_img(img.get("src")) is False:
                img.decompose()

        # Trouves les tags "font" et change l'attribut size en font-size
        for font in content.find_all("font"):
            font: BeautifulSoup
            if font.attrs.get("size"):

                # En fonction de sa valeur, on lui attribue une date
                size = int(font.attrs['size'])
                new_size: str = "smaller"
                if size < 4:
                    new_size = "smaller"
                else:
                    new_size = "small"

                # on ajoute l'attribut "style" avec le bon font-size
                font.attrs["style"] = f"font-size:{new_size};"
                font.attrs.pop("size")

        # Enlèves les tags 'embed
        for embed in content.find_all("embed"):
            embed: BeautifulSoup
            embed.decompose()

        return content

    def __check_comment_article(self, comments: list[Commentaire]) -> list[BeautifulSoup]:

        new_comments: list[BeautifulSoup] = []

        # Ajoutes les commentaires
        for comment in list(reversed(comments)):

            # copie le modèle de commentaire
            new_comment = deepcopy(self.soup_comment)

            # ajoute les métadonnée dans les bons tags
            new_comment.find(
                "div", {"class": "comment_user"}).string = comment.auteur
            new_comment.find("div", {"class": "comment_user"}).append(
                BeautifulSoup('<span class=\"comment_date\"></span>', "lxml"))
            new_comment.find("span", {"class": "comment_date"}).string = datetime.fromisoformat(
                comment.date).strftime("%A %d %B %Y")
            new_comment.find("div", {"class": "comment_text"}).append(
                BeautifulSoup(comment.content, 'html.parser'))
            new_comments.append(new_comment)

        print(f"{len(new_comments)} commentaires au total.")
        # retourne les nouveaux commentaires
        return new_comments

    def convert(self, article: Article, save_html: bool = False) -> None:

        # Lances le timer
        timer = time.time_ns()

        file_converting = f"{datetime.fromisoformat(article.date).strftime('%d-%m-%Y')}_{article.title.replace(' ','_').strip()}"
        print(f"Début de la conversion de `{file_converting}.txt`")

        soup = deepcopy(self.soup)

        # Attribue le titre et la date à la page
        soup.find("h1", {"id": "title"}).string = article.title
        soup.find("h2", {"id": "date"}).string = datetime.fromisoformat(
            article.date).strftime("%A %d %B %Y")

        # Analyse le contenu de la page en HTML
        content = BeautifulSoup(article.body, 'html.parser')

        # Ajoute le contenu de l'article à la page html

        soup.find("div", {"id": "content"}).append(
            self.__check_contenu_article(content))
        if article.commentaires is not None:
            soup.find("div", {"id": "comments"}).extend(
                self.__check_comment_article(article.commentaires))

            if len(content.text) > 5932:
                soup.find("div", {"id": "content"}
                          ).attrs['style'] = "page-break-after: always;"

        if save_html is True:
            open(f"{file_converting}.html", "+w").write(soup.prettify())

        HTML(string=soup.prettify()).write_pdf(f"output/{file_converting}.pdf")
        print(
            f"fin de la conversion de `{file_converting}.pdf` en: {(time.time_ns() - timer) / 1000000000}")
