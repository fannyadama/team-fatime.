from datetime import datetime

# --- FONCTION RAPPORT SHEICKNER ---
@app.post("/sheickner/report")
async def generate_report(contact_id: str):
    """
    SHEICKNER génère un rapport hebdomadaire pour un client.
    Exécute ce endpoint chaque vendredi via un cron job.
    """
    # TODO : Récupérer les vraies données depuis Vendasta
    # Mock data pour l'instant
    mock_data = {
        "posts_created": 3,
        "campaigns_sent": 1,
        "leads_contacted": 12,
        "appointments_booked": 3,
        "reviews_collected": 5,
        "period": "Semaine du 10 au 16 août 2026"
    }

    report_prompt = f"""
    Tu es SHEICKNER, le Boss de TEAM FATIME.
    Rédige un rapport hebdomadaire professionnel, chaleureux, en français.
    Vous vouvoyez le client.
    Données de la semaine :
    - Posts créés : {mock_data['posts_created']}
    - Campagnes envoyées : {mock_data['campaigns_sent']}
    - Leads contactés : {mock_data['leads_contacted']}
    - RDV pris : {mock_data['appointments_booked']}
    - Avis Google collectés : {mock_data['reviews_collected']}

    Structure :
    1. Introduction : "Bonjour Monsieur/Madame, voici le rapport de votre équipe cette semaine."
    2. Ce qui a été fait
    3. Les résultats
    4. Prochaines actions recommandées
    5. Fin : "Bonne fin de semaine, SHEICKNER"
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": report_prompt}],
        temperature=0.7
    )

    report = response.choices[0].message.content

    # Sauvegarder dans le CRM
    save_to_crm(
        contact_id=contact_id,
        note=f"Rapport hebdomadaire SHEICKNER : {report}",
        agent="SHEICKNER"
    )

    return {
        "agent": "SHEICKNER",
        "report": report,
        "contact_id": contact_id
    }
