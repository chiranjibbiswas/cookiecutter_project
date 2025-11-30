# api/generate.py
def handler(request):
    try:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"message": "Python function executed successfully"}'
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"error": "' + str(e) + '"}'
        }
