from src.intent.classifier import IntentClassifier


def test_valid_deletion_requests():
    texts = [
        "Please permanently delete the account associated with this email address.",
        "I am requesting deletion of the account registered to this email address.",
        "Je demande la suppression définitive du compte associé à cette adresse e-mail.",
        "Por favor elimine mi cuenta y todos mis datos personales asociados.",
        "Bitte löschen Sie mein Konto und alle damit verbundenen persönlichen Daten.",
        "アカウントの完全な削除を依頼します。",
        "계정과 관련된 모든 개인 정보를 영구적으로 삭제해 주시기 바랍니다.",
    ]
    for t in texts:
        assert IntentClassifier.is_deletion_request(t) is True


def test_non_deletion_requests():
    non_del_texts = [
        "The mobile number on my profile is out of date. Please replace it with the new one and leave the account active.",
        "Please stop the promotional emails. I still need the account and my order history, so I am not asking for deletion.",
        "I'd like to download my account information in a portable format. Please keep the account as it is.",
        "My surname is misspelled on the account. Can you correct it without removing any of my records?",
        "I need a copy of last year's invoices for my records. Please leave my profile and purchase history in place.",
        "Please change the email address used for this account. I want to continue using the service.",
        "Ne souhaite pas supprimer mon compte, simplement me désabonner de la newsletter.",
        "Dejar la cuenta activa, solo corregir la dirección de envío.",
        "계정을 유지하고 마케팅 이메일만 중단해 주세요.",
    ]
    for t in non_del_texts:
        assert IntentClassifier.is_deletion_request(t) is False
