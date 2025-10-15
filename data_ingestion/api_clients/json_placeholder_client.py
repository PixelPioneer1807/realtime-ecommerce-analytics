"""
Client for JSONPlaceholder API to fetch user data.
API Documentation: https://jsonplaceholder.typicode.com/
"""

import requests
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class JSONPlaceholderClient:
    """Client to interact with JSONPlaceholder API for user data"""
    
    BASE_URL = "https://jsonplaceholder.typicode.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RealTimeEcommerceAnalytics/1.0'
        })
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Fetch all users from the API.
        
        Returns:
            List of user dictionaries
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/users", timeout=10)
            response.raise_for_status()
            users = response.json()
            
            logger.info(f"Successfully fetched {len(users)} users")
            return users
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching users: {e}")
            return []
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single user by ID.
        
        Args:
            user_id: User ID to fetch
            
        Returns:
            User dictionary or None if not found
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/users/{user_id}", 
                timeout=10
            )
            response.raise_for_status()
            user = response.json()
            
            logger.info(f"Successfully fetched user ID: {user_id}")
            return user
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def get_user_posts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Fetch posts by a specific user (can simulate browsing history).
        
        Args:
            user_id: User ID
            
        Returns:
            List of post dictionaries
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/posts?userId={user_id}", 
                timeout=10
            )
            response.raise_for_status()
            posts = response.json()
            
            logger.info(f"Successfully fetched {len(posts)} posts for user {user_id}")
            return posts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching posts for user {user_id}: {e}")
            return []
    
    def close(self):
        """Close the session"""
        self.session.close()


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = JSONPlaceholderClient()
    
    # Test fetching all users
    users = client.get_all_users()
    print(f"\nTotal users: {len(users)}")
    
    # Test fetching single user
    if users:
        user = client.get_user_by_id(1)
        print(f"\nSample user: {user}")
        
        # Test fetching user posts
        posts = client.get_user_posts(1)
        print(f"\nUser 1 has {len(posts)} posts")
    
    client.close()
