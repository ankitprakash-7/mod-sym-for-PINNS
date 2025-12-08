#!/usr/bin/env python3
"""
Test script for React Code Editor API
"""

import requests
import json
import sys
import time

API_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    response = requests.get(f"{API_URL}/health")
    
    if response.status_code == 200:
        print("✅ Health check passed")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print("❌ Health check failed")
        return False


def test_edit(app_id="test-app", msg_id="v1", instruction=None):
    """Test edit endpoint"""
    if instruction is None:
        instruction = "Change the Play button color from blue to green"
    
    print(f"\n🎯 Testing edit...")
    print(f"App ID: {app_id}")
    print(f"Message ID: {msg_id}")
    print(f"Instruction: {instruction}")
    print()
    
    payload = {
        "app_id": app_id,
        "msg_id": msg_id,
        "instruction": instruction
    }
    
    print("📤 Sending request...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/edit",
            json=payload,
            timeout=120  # 2 minutes timeout
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️  Request completed in {elapsed:.2f} seconds")
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("✅ Edit successful!")
                print()
                print("📝 Summary:")
                print(f"   Files modified: {len(result.get('files_modified', []))}")
                print(f"   Files added: {len(result.get('files_added', []))}")
                print(f"   Packages added: {len(result.get('packages_added', []))}")
                print()
                
                if result.get('files_modified'):
                    print("   Modified files:")
                    for f in result['files_modified']:
                        print(f"   • {f}")
                    print()
                
                if result.get('files_added'):
                    print("   Added files:")
                    for f in result['files_added']:
                        print(f"   • {f}")
                    print()
                
                if result.get('packages_added'):
                    print("   Added packages:")
                    for pkg in result['packages_added']:
                        print(f"   • {pkg}")
                    print()
                
                if result.get('explanation'):
                    print(f"   Explanation: {result['explanation']}")
                    print()
                
                if result.get('debug_info'):
                    debug = result['debug_info']
                    print("   Debug info:")
                    print(f"   • Selected files: {debug.get('selected_files_count')}")
                    print(f"   • Scope: {debug.get('estimated_scope')}")
                    print(f"   • Confidence: {debug.get('confidence')}")
                    print()
                
                return True
            else:
                print("❌ Edit failed!")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main test runner"""
    print("="*60)
    print("React Code Editor API - Test Script")
    print("="*60)
    print()
    
    # Test health
    if not test_health():
        print("\n⚠️  Health check failed. Is the API running?")
        print("   Start it with: python app.py")
        sys.exit(1)
    
    # Test edit
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
        success = test_edit(instruction=instruction)
    else:
        # Run default tests
        print("\n" + "="*60)
        print("Running default test scenarios...")
        print("="*60)
        
        tests = [
            "Change the Play button color from blue to green",
            "Add a Delete button next to the Skip Forward button",
            "Make the song title text larger",
        ]
        
        for i, instruction in enumerate(tests, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(tests)}")
            print(f"{'='*60}")
            success = test_edit(instruction=instruction)
            
            if not success:
                print(f"\n⚠️  Test {i} failed")
                break
            
            if i < len(tests):
                print("\n⏸️  Waiting 2 seconds before next test...")
                time.sleep(2)
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
