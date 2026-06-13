from playwright.sync_api import sync_playwright
import re

def instantgaming_search(
    search_query,
    platform=None,
    type_value=None,
    gametype=None,
    latam_priority=True,
    max_details=6,
    concurrency=6,
):
    q = str(search_query or '').strip()
    url = f"https://www.instant-gaming.com/pt/pesquisar/?query={q}"

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        context = browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        try:
            print(f"[IG] Acessando: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"[IG] Página carregada, título: {page.title()}")

            # Espera os cards de produto aparecerem
            page.wait_for_selector("article.item", timeout=15000)
            print("[IG] Seletor article.item encontrado")

            articles = page.query_selector_all("article.item")
            print(f"[IG] Total de articles encontrados: {len(articles)}")

            for article in articles:
                try:
                    title_el = article.query_selector("span.title")
                    link_el = article.query_selector("a.cover")
                    price_el = article.query_selector("div.price")

                    if not title_el or not link_el:
                        continue

                    title = title_el.inner_text().strip()
                    href = link_el.get_attribute("href") or ""
                    full_link = href if href.startswith("http") else f"https://www.instant-gaming.com{href}"
                    price_text = price_el.inner_text().strip() if price_el else ""

                    if title and price_text:
                        results.append({
                            "title": title,
                            "price": price_text,
                            "link": full_link,
                            "origin": "Instant Gaming"
                        })
                except Exception:
                    continue

            # Enriquecimento LATAM nos primeiros N resultados
            if latam_priority and results:
                for entry in results[:max(0, int(max_details))]:
                    try:
                        prod_page = context.new_page()
                        prod_page.goto(entry["link"], wait_until="networkidle", timeout=20000)

                        # Tenta encontrar opção Latin America
                        la_option = prod_page.query_selector("option:has-text('Latin America')")
                        if not la_option:
                            la_option = prod_page.query_selector("li.option:has-text('Latin America')")

                        if la_option:
                            la_price = la_option.get_attribute("data-product-price") or ""
                            la_href = la_option.get_attribute("data-href") or ""
                            la_id = la_option.get_attribute("data-value") or ""

                            if la_price:
                                entry["price"] = la_price.strip()
                            if la_href:
                                entry["link"] = la_href.strip()
                            elif la_id:
                                entry["link"] = re.sub(
                                    r'(/pt/)(\d+)(-)',
                                    lambda m: m.group(1) + la_id + m.group(3),
                                    entry["link"]
                                )

                        prod_page.close()
                    except Exception:
                        try:
                            prod_page.close()
                        except Exception:
                            pass
                        continue

        except Exception as e:
            print(f"[IG] ERRO Playwright: {type(e).__name__}: {e}")
            try:
                print(f"[IG] HTML atual (500 chars): {page.content()[:500]}")
            except Exception:
                pass
        finally:
            browser.close()

    return results
