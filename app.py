from datetime import date, timedelta

import streamlit as st


st.set_page_config(
    page_title="AI Travel Concierge",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ AI Travel Concierge")
st.write("Enter your travel details to generate a basic trip itinerary.")

activity_options = {
    "Adventure": [
        "Try a popular adventure activity",
        "Visit a nearby viewpoint",
        "Explore an outdoor attraction",
    ],
    "Beaches": [
        "Relax at a popular beach",
        "Enjoy beachside activities",
        "Watch the sunset near the coast",
    ],
    "Food": [
        "Try famous local dishes",
        "Visit a popular local restaurant",
        "Explore a local food market",
    ],
    "History": [
        "Visit a historical monument",
        "Explore a museum",
        "Take a heritage walk",
    ],
    "Nature": [
        "Visit a park or garden",
        "Explore a scenic natural location",
        "Take a peaceful nature walk",
    ],
    "Shopping": [
        "Visit a popular shopping area",
        "Explore a local market",
        "Shop for souvenirs",
    ],
    "Temples": [
        "Visit a famous temple",
        "Explore an important spiritual place",
        "Attend a local cultural or religious activity",
    ],
}

with st.form("travel_form"):
    col1, col2 = st.columns(2)

    with col1:
        origin = st.text_input("Starting city")
        destination = st.text_input("Destination")

        departure_date = st.date_input(
            "Departure date",
            value=date.today() + timedelta(days=1),
        )

    with col2:
        return_date = st.date_input(
            "Return date",
            value=date.today() + timedelta(days=4),
        )

        travellers = st.number_input(
            "Number of travellers",
            min_value=1,
            max_value=20,
            value=1,
        )

        budget = st.number_input(
            "Total budget in ₹",
            min_value=0,
            value=20000,
            step=1000,
        )

    interests = st.multiselect(
        "Select your interests",
        list(activity_options.keys()),
        default=["Food", "Nature"],
    )

    submit_button = st.form_submit_button("Plan My Trip")

if submit_button:
    origin = origin.strip()
    destination = destination.strip()

    if not origin or not destination:
        st.error("Please enter both the starting city and destination.")

    elif return_date < departure_date:
        st.error("Return date must be after the departure date.")

    else:
        number_of_days = (return_date - departure_date).days + 1
        selected_interests = interests or ["Nature", "Food"]

        st.success(
            f"Your {number_of_days}-day trip from "
            f"{origin} to {destination} has been generated."
        )

        st.subheader("🧳 Trip Summary")

        summary_col1, summary_col2, summary_col3 = st.columns(3)

        summary_col1.metric("Destination", destination)
        summary_col2.metric("Travellers", int(travellers))
        summary_col3.metric("Budget", f"₹{budget:,.0f}")

        estimated_daily_budget = budget / number_of_days

        st.write(f"**Travel dates:** {departure_date} to {return_date}")
        st.write(f"**Interests:** {', '.join(selected_interests)}")
        st.write(
            f"**Estimated daily budget:** "
            f"₹{estimated_daily_budget:,.0f}"
        )

        st.divider()
        st.subheader("🗓️ Day-by-Day Itinerary")

        itinerary_lines = [
            f"Trip from {origin} to {destination}",
            f"Dates: {departure_date} to {return_date}",
            f"Travellers: {int(travellers)}",
            f"Budget: ₹{budget:,.0f}",
            "",
        ]

        for day_number in range(1, number_of_days + 1):
            current_date = departure_date + timedelta(days=day_number - 1)

            interest = selected_interests[
                (day_number - 1) % len(selected_interests)
            ]

            activities = activity_options[interest]

            morning_activity = activities[0]
            afternoon_activity = activities[1]
            evening_activity = activities[2]

            with st.expander(
                f"Day {day_number} – {current_date}",
                expanded=True,
            ):
                if day_number == 1:
                    st.write(
                        f"**Morning:** Travel from {origin} "
                        f"to {destination} and check in."
                    )
                else:
                    st.write(f"**Morning:** {morning_activity}.")

                st.write(f"**Afternoon:** {afternoon_activity}.")
                st.write(f"**Evening:** {evening_activity}.")
                st.write(
                    f"**Suggested daily spending limit:** "
                    f"₹{estimated_daily_budget:,.0f}"
                )

            itinerary_lines.extend(
                [
                    f"Day {day_number} – {current_date}",
                    f"Morning: {morning_activity}",
                    f"Afternoon: {afternoon_activity}",
                    f"Evening: {evening_activity}",
                    (
                        "Suggested spending limit: "
                        f"₹{estimated_daily_budget:,.0f}"
                    ),
                    "",
                ]
            )

        st.info(
            "This is currently a basic generated itinerary. "
            "Real places, weather and flights will be added through APIs."
        )

        itinerary_text = "\n".join(itinerary_lines)

        st.download_button(
            label="Download Itinerary",
            data=itinerary_text,
            file_name="travel_itinerary.txt",
            mime="text/plain",
        )
        