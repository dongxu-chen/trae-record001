import sys
sys.path.insert(0, '.')

from web import create_app

app = create_app()
client = app.test_client()

print('Testing API endpoints...')

print('\n1. Testing /api/health:')
response = client.get('/api/health')
print(f'   Status: {response.status_code}')
print(f'   Data: {response.get_json()}')

print('\n2. Testing /api/dashboard:')
response = client.get('/api/dashboard?hours=24')
print(f'   Status: {response.status_code}')
data = response.get_json()
print(f'   Keys: {list(data.keys())}')
dist = data.get('sentiment_distribution', {})
print(f'   Sentiment distribution: {dist}')

print('\n3. Testing /api/analyze:')
response = client.post('/api/analyze', 
    json={'text': '这个产品真的太棒了，非常满意！'})
print(f'   Status: {response.status_code}')
result = response.get_json()
print(f'   Sentiment: {result.get("sentiment", {})}')
print(f'   Keywords: {result.get("keywords", [])}')

print('\n4. Testing /api/data/generate:')
response = client.post('/api/data/generate', json={'count': 20})
print(f'   Status: {response.status_code}')
print(f'   Result: {response.get_json()}')

print('\n5. Testing /api/alerts:')
response = client.get('/api/alerts?limit=10')
print(f'   Status: {response.status_code}')
print(f'   Alerts count: {len(response.get_json())}')

print('\n6. Testing /api/sentiment:')
response = client.get('/api/sentiment?hours=24')
print(f'   Status: {response.status_code}')
print(f'   Result: {response.get_json()}')

print('\n7. Testing /api/trends:')
response = client.get('/api/trends?hours=24')
print(f'   Status: {response.status_code}')
trends = response.get_json()
print(f'   Trend data points: {len(trends)}')

print('\n8. Testing /api/keywords:')
response = client.get('/api/keywords?hours=24&top_k=10')
print(f'   Status: {response.status_code}')
keywords = response.get_json()
print(f'   Top keywords: {keywords[:5]}')

print('\n9. Testing /api/stats:')
response = client.get('/api/stats?hours=24')
print(f'   Status: {response.status_code}')
print(f'   Platform stats: {response.get_json()}')

print('\n10. Testing /api/topics:')
response = client.get('/api/topics')
print(f'   Status: {response.status_code}')
topics = response.get_json()
print(f'   Topics count: {len(topics)}')

print('\n✅ All API tests completed!')
