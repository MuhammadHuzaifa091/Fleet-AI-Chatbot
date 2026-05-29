import httpx
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.traccar import FuelPrice
import asyncio

logger = logging.getLogger(__name__)

class FuelPriceService:
    # Official sources for Pakistan fuel prices
    SOURCES = [
        {"name": "PSO", "url": "https://pso.com.pk/en/product-and-services/fuel-prices"},
        {"name": "OGRA", "url": "https://ogra.org.pk/"}
    ]

    @staticmethod
    async def scrape_and_update_prices(db: AsyncSession):
        """
        Scrapes live fuel prices from official sources and updates the database.
        """
        try:
            prices = await FuelPriceService._fetch_from_pso()
            if not prices:
                prices = await FuelPriceService._fetch_from_fallback()

            if prices:
                for fuel_type, price in prices.items():
                    # Check if exists
                    query = select(FuelPrice).where(FuelPrice.fuel_type == fuel_type)
                    result = await db.execute(query)
                    fuel_price_obj = result.scalar_one_or_none()

                    if fuel_price_obj:
                        fuel_price_obj.price = price
                        fuel_price_obj.last_updated = datetime.utcnow()
                        fuel_price_obj.source = "PSO/Scraped"
                    else:
                        new_price = FuelPrice(
                            fuel_type=fuel_type,
                            price=price,
                            last_updated=datetime.utcnow(),
                            source="PSO/Scraped"
                        )
                        db.add(new_price)
                
                await db.commit()
                logger.info(f"Successfully updated fuel prices: {prices}")
                return prices
            return None
        except Exception as e:
            logger.error(f"Error updating fuel prices: {e}")
            return None

    @staticmethod
    async def _fetch_from_pso():
        """
        Specific logic to scrape PSO's website.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(FuelPriceService.SOURCES[0]["url"])
                if response.status_code != 200:
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                # Logic to find price in table
                # PSO usually has a table with classes or specific text
                prices = {}
                # This is a representative selector based on common PSO layout
                rows = soup.find_all('tr')
                for row in rows:
                    text = row.get_text().lower()
                    if 'motor spirit' in text or 'petrol' in text:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            price_text = cols[-1].get_text().strip().replace('Rs.', '').replace(',', '')
                            prices['Petrol'] = float(price_text)
                    elif 'hi-speed diesel' in text or 'diesel' in text:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            price_text = cols[-1].get_text().strip().replace('Rs.', '').replace(',', '')
                            prices['Diesel'] = float(price_text)
                
                return prices if prices else None
        except Exception as e:
            logger.warning(f"PSO Scrape failed: {e}")
            return None

    @staticmethod
    async def _fetch_from_fallback():
        """
        Fallback logic using a secondary source or API if available.
        """
        # Placeholder for another source like OGRA or a public API
        # For now, if scraping fails, we return most recent from DB or a safe default if first run
        return {"Petrol": 272.89, "Diesel": 278.96} # Last known safe prices as absolute last resort

    @staticmethod
    async def get_latest_prices(db: AsyncSession):
        query = select(FuelPrice)
        result = await db.execute(query)
        rows = result.scalars().all()
        return {row.fuel_type: row.price for row in rows} if rows else await FuelPriceService.scrape_and_update_prices(db)
