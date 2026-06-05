from app import app
app.testing=True
client=app.test_client()
rv=client.get('/api/device/status')
print('status', rv.status_code)
print(rv.get_data(as_text=True))
