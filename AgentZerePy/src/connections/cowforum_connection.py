import logging
import requests
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional
from src.connections.base_connection import BaseConnection, Action, ActionParameter
from datetime import datetime

logger = logging.getLogger("connections.cowforum")

BROWSERLESS_URL = "http://localhost:3000/content"


class CowForumConnection(BaseConnection):
    def __init__(self, config):
        self.forum_url = config.get("forum_url", "https://forum.cow.fi")
        super().__init__(config)

    @property
    def is_llm_provider(self):
        return False

    def validate_config(self, config) -> Dict[str, Any]:
        if "forum_url" in config and not isinstance(config["forum_url"], str):
            raise ValueError("forum_url must be a string")
        return config

    def configure(self, **kwargs) -> bool:
        return True

    def is_configured(self, verbose=True) -> bool:
        try:
            self._test_connection()
            if verbose:
                logger.info("✅ Browserless connection test successful")
            return True
        except Exception as e:
            if verbose:
                logger.error(f"Configuration check failed: {str(e)}")
            return False

    def _test_connection(self) -> None:
        """Test if Browserless is accessible"""
        try:
            payload = {
                "url": "https://example.com",
                "waitForTimeout": 1000,
            }
            response = requests.post(
                BROWSERLESS_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            if not response.text:
                raise Exception("Empty response from Browserless")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection test failed - Network error: {str(e)}")
        except Exception as e:
            raise Exception(f"Connection test failed: {str(e)}")

    def _browserless_query(self, url: str, selector: Optional[str] = None) -> str:
        """Execute a content query using Browserless"""
        payload = {
            "url": url,
            "waitForTimeout": 3000,
            "bestAttempt": True,
            # "launchOptions": {"args": ["--proxy-server=91.108.238.117:8000"]},
        }

        if selector:
            payload["waitForSelector"] = {
                "selector": selector,
                "timeout": 5000,
                "visible": True,
            }

        try:
            response = requests.post(
                BROWSERLESS_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Browserless query failed - Network error: {str(e)}")
        except Exception as e:
            raise Exception(f"Browserless query failed: {str(e)}")

    def get_forum_updates(
        self, category: Optional[str] = None, limit: Optional[int] = 10
    ) -> List[Dict]:
        try:
            html = self._browserless_query(
                self.forum_url, selector=".latest-topic-list"
            )

            if not html:
                logger.error("Empty response from Browserless")
                return []

            soup = BeautifulSoup(html, "html.parser")
            topics_container = soup.find("div", class_="latest-topic-list")
            if not topics_container:
                logger.error("Could not find topics container")
                return []

            topics = topics_container.find_all("div", class_="latest-topic-list-item")
            posts = []
            for topic in topics:
                try:
                    # Extract data using BeautifulSoup
                    topic_id = topic.get("data-topic-id")
                    title_elem = topic.find("a", class_="title")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    href = title_elem.get("href") if title_elem else ""

                    category_elem = topic.find("span", class_="badge-category__name")
                    category_text = (
                        category_elem.get_text(strip=True) if category_elem else ""
                    )

                    author_img = topic.find("img", class_="avatar")
                    author = author_img.get("title") if author_img else ""

                    date_elem = topic.find("span", class_="relative-date")
                    timestamp = int(date_elem.get("data-time")) if date_elem else None

                    replies_elem = topic.find("span", class_="number")
                    replies = (
                        int(replies_elem.get_text(strip=True)) if replies_elem else 0
                    )

                    post = {
                        "id": topic_id,
                        "title": title,
                        "url": f"{self.forum_url}{href}",
                        "category": category_text,
                        "author": author,
                        "date": (
                            datetime.fromtimestamp(timestamp / 1000).isoformat()
                            if timestamp
                            else datetime.now().isoformat()
                        ),
                        "replies": replies,
                    }

                    if category and post["category"].lower() != category.lower():
                        continue

                    posts.append(post)
                    if len(posts) >= limit:
                        break

                except Exception as e:
                    logger.error(f"Failed to parse forum post: {str(e)}")
                    continue

            logger.info(f"Retrieved {len(posts)} forum posts")
            return posts

        except Exception as e:
            logger.error(f"Failed to get forum updates: {str(e)}")
            return []

    def get_forum_article(self, url: str) -> Optional[Dict]:
        try:
            html = self._browserless_query(url, selector=".cooked")
            print(html)  # dont delete this print

            if not html:
                logger.error("Empty response from Browserless")
                return None

            soup = BeautifulSoup(html, "html.parser")
            article_content = soup.find("div", class_="cooked")
            if not article_content:
                logger.error("Could not find article content")
                return None

            try:
                # Get title from the first h1
                title = article_content.find("h1")
                title_text = title.get_text(strip=True) if title else ""

                # Remove code blocks buttons and other non-content elements
                for elem in article_content.find_all(
                    "div", class_="codeblock-button-wrapper"
                ):
                    elem.decompose()
                for elem in article_content.find_all(
                    "div", class_="cooked-selection-barrier"
                ):
                    elem.decompose()

                # Get all content excluding title
                content_elems = article_content.find_all(
                    ["p", "pre", "h2", "h3", "ul", "ol", "blockquote"]
                )
                content = "\n\n".join(
                    elem.get_text(strip=True) for elem in content_elems
                )

                # Extract metadata from the first code block if it exists
                metadata = {}
                code_block = article_content.find("code", class_="hljs")
                if code_block:
                    for line in code_block.get_text().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()

                article = {
                    "title": title_text,
                    "content": content,
                    "metadata": metadata,
                }

                logger.info(f"Retrieved article: {article['title']}")
                return article

            except Exception as e:
                logger.error(f"Failed to parse article content: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Failed to get forum article: {str(e)}")
            return None

    def register_actions(self) -> None:
        self.actions = {
            "get-forum-updates": Action(
                name="get-forum-updates",
                parameters=[
                    ActionParameter(
                        "category",
                        False,
                        str,
                        "Category to filter posts (e.g., 'governance', 'development')",
                    ),
                    ActionParameter(
                        "limit",
                        False,
                        int,
                        "Maximum number of posts to retrieve",
                    ),
                ],
                description="Get latest updates from the CoW Protocol forum",
            ),
            "get-forum-article": Action(
                name="get-forum-article",
                parameters=[
                    ActionParameter(
                        "url",
                        True,
                        str,
                        "URL of the forum article to parse",
                    ),
                ],
                description="Get content of a specific forum article",
            ),
        }

    def perform_action(self, action_name: str, kwargs) -> Any:
        """Perform an action with the given parameters"""
        if action_name not in self.actions:
            raise KeyError(f"Unknown action: {action_name}")

        action = self.actions[action_name]
        errors = action.validate_params(kwargs)
        if errors:
            raise ValueError(f"Invalid parameters: {', '.join(errors)}")

        method_name = action_name.replace("-", "_")
        method = getattr(self, method_name)
        return method(**kwargs)
