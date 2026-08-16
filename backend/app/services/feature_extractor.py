import re
from urllib.parse import urlparse

class FeatureExtractor:
    """
    Extracts lexical, structural, and content-based features from a URL 
    to match the exact 50-feature input matrix required by the ML models.
    """
    
    def __init__(self):
        # The exact order of features expected by the trained XGBoost model
        # (excluding the dropped 'FILENAME', 'URL', 'Domain', 'TLD', 'Title', and 'label')
        self.feature_columns = [
            'URLLength', 'DomainLength', 'IsDomainIP', 'URLSimilarityIndex', 
            'CharContinuationRate', 'TLDLegitimateProb', 'URLCharProb', 'TLDLength', 
            'NoOfSubDomain', 'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio', 
            'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL', 
            'NoOfEqualsInURL', 'NoOfQMarkInURL', 'NoOfAmpersandInURL', 'NoOfOtherSpecialCharsInURL', 
            'SpacialCharRatioInURL', 'IsHTTPS', 'LineOfCode', 'LargestLineLength', 'HasTitle', 
            'DomainTitleMatchScore', 'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 
            'NoOfURLRedirect', 'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 'NoOfiFrame', 
            'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton', 'HasHiddenFields', 
            'HasPasswordField', 'Bank', 'Pay', 'Crypto', 'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 
            'NoOfJS', 'NoOfSelfRef', 'NoOfEmptyRef', 'NoOfExternalRef'
        ]

    def extract(self, url: str, scraped_data: dict = None) -> dict:
        """
        Takes a raw URL and an optional dictionary of scraped content features.
        Returns a dictionary of all computed features ready for the ML model.
        """
        if scraped_data is None:
            scraped_data = {}

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path

        features = {}

        # 1. Length-based Features
        features['URLLength'] = len(url)
        features['DomainLength'] = len(domain)
        
        # 2. Domain & TLD Features
        features['IsDomainIP'] = 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain) else 0
        tld = domain.split('.')[-1] if '.' in domain else ''
        features['TLDLength'] = len(tld)
        features['NoOfSubDomain'] = max(0, len(domain.split('.')) - 2) if not features['IsDomainIP'] else 0
        features['IsHTTPS'] = 1 if parsed_url.scheme == 'https' else 0

        # 3. Character Count Features
        letters = len(re.findall(r'[a-zA-Z]', url))
        digits = len(re.findall(r'[0-9]', url))
        special_chars = len(re.sub(r'[a-zA-Z0-9]', '', url))
        
        features['NoOfLettersInURL'] = letters
        features['LetterRatioInURL'] = letters / len(url) if len(url) > 0 else 0
        features['NoOfDegitsInURL'] = digits
        features['DegitRatioInURL'] = digits / len(url) if len(url) > 0 else 0
        features['NoOfEqualsInURL'] = url.count('=')
        features['NoOfQMarkInURL'] = url.count('?')
        features['NoOfAmpersandInURL'] = url.count('&')
        features['NoOfOtherSpecialCharsInURL'] = special_chars
        features['SpacialCharRatioInURL'] = special_chars / len(url) if len(url) > 0 else 0

        # 4. Advanced / Probabilistic Features (Baseline estimates for live extraction)
        # In a full production environment, these would be computed against a live dataset or frequency table
        features['URLSimilarityIndex'] = 100.0  
        features['CharContinuationRate'] = 1.0  
        features['TLDLegitimateProb'] = 0.5     
        features['URLCharProb'] = 0.05          
        features['HasObfuscation'] = 0
        features['NoOfObfuscatedChar'] = 0
        features['ObfuscationRatio'] = 0.0

        # 5. Content-Based Features (Requires scraper.py)
        # We initialize them safely to 0 and update them if `scraped_data` was successfully fetched
        content_feature_keys = [
            'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore', 
            'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 'NoOfURLRedirect', 
            'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 'NoOfiFrame', 'HasExternalFormSubmit', 
            'HasSocialNet', 'HasSubmitButton', 'HasHiddenFields', 'HasPasswordField', 'Bank', 'Pay', 
            'Crypto', 'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 'NoOfJS', 'NoOfSelfRef', 
            'NoOfEmptyRef', 'NoOfExternalRef'
        ]

        for cf in content_feature_keys:
            features[cf] = scraped_data.get(cf, 0)

        # 6. Ensure strict column ordering
        ordered_features = {col: features.get(col, 0) for col in self.feature_columns}
        return ordered_features

#for testing:
if __name__ == "__main__":
    extractor = FeatureExtractor()
    sample_url = "https://www.paypal-secure-login-update.com/verify?id=12345"
    
    # Simulating failed scrape by passing an empty dictionary
    result = extractor.extract(sample_url, scraped_data={})
    print(f"Extracted {len(result)} features for prediction.")