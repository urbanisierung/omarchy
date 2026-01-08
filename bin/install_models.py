#!/usr/bin/env python3
import argostranslate.package
import argostranslate.translate

def install():
    print("Updating package index...")
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    
    # Define the languages you want to cross-reference
    # This will install pairs like en->de, de->en, es->en, en->es, etc.
    desired_codes = ["en", "de", "es", "fr"] 
    
    print(f"Installing models for: {', '.join(desired_codes)}...")
    print("This may take a few minutes (approx 500MB)...")
    
    count = 0
    for pkg in available_packages:
        if pkg.from_code in desired_codes and pkg.to_code in desired_codes:
            print(f"Downloading {pkg.from_code} -> {pkg.to_code}...")
            argostranslate.package.install_from_path(pkg.download())
            count += 1
            
    print(f"\nSuccess! Installed {count} language models.")

if __name__ == "__main__":
    install()