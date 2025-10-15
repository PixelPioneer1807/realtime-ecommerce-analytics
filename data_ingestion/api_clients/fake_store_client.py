"""
Client for Fake Store API to fetch product data.
API Documentation: https://fakestoreapi.com/docs
"""

import requests
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FakeStoreClient:
    """Client to interact with Fake Store API"""
    
    BASE_URL = "https://fakestoreapi.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RealTimeEcommerceAnalytics/1.0'
        })
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """
        Fetch all products from the API.
        
        Returns:
            List of product dictionaries
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/products", timeout=10)
            response.raise_for_status()
            products = response.json()
            
            logger.info(f"Successfully fetched {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching products: {e}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single product by ID.
        
        Args:
            product_id: Product ID to fetch
            
        Returns:
            Product dictionary or None if not found
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/products/{product_id}", 
                timeout=10
            )
            response.raise_for_status()
            product = response.json()
            
            logger.info(f"Successfully fetched product ID: {product_id}")
            return product
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Fetch products in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of product dictionaries
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/products/category/{category}", 
                timeout=10
            )
            response.raise_for_status()
            products = response.json()
            
            logger.info(f"Successfully fetched {len(products)} products in category: {category}")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching category {category}: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """
        Fetch all available product categories.
        
        Returns:
            List of category names
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/products/categories", 
                timeout=10
            )
            response.raise_for_status()
            categories = response.json()
            
            logger.info(f"Successfully fetched {len(categories)} categories")
            return categories
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching categories: {e}")
            return []
    
    def enrich_product_event(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich product data with additional fields for event schema.
        
        Args:
            product: Raw product data from API
            
        Returns:
            Enriched product event dictionary
        """
        import random
        
        event = {
            "event_id": f"prod_{product['id']}_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "product_id": product.get("id"),
            "title": product.get("title"),
            "price": product.get("price"),
            "category": product.get("category"),
            "description": product.get("description"),
            "image": product.get("image"),
            "rating_rate": product.get("rating", {}).get("rate"),
            "rating_count": product.get("rating", {}).get("count"),
            "stock_quantity": random.randint(10, 200)  # Simulated stock level
        }
        
        return event
    
    def close(self):
        """Close the session"""
        self.session.close()


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = FakeStoreClient()
    
    # Test fetching all products
    products = client.get_all_products()
    print(f"\nTotal products: {len(products)}")
    
    # Test fetching categories
    categories = client.get_all_categories()
    print(f"\nCategories: {categories}")
    
    # Test fetching single product
    if products:
        product = client.get_product_by_id(1)
        print(f"\nSample product: {product}")
        
        # Test enrichment
        enriched = client.enrich_product_event(product)
        print(f"\nEnriched event: {enriched}")
    
    client.close()
