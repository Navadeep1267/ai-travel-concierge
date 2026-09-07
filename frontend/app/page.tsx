"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function Home() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim() || loading) return;

    const userMessage = message.trim();

    // Show user's message immediately
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: userMessage,
      },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Backend error");
      }

      // Show AI response
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.answer,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            error instanceof Error
              ? `⚠️ ${error.message}`
              : "⚠️ Could not connect to the travel assistant.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const planTokyoTrip = () => {
    setMessage("Plan a 3-day trip to Tokyo");
  };

  const checkParisWeather = () => {
    setMessage("What is the weather in Paris?");
  };

  const exploreJapan = () => {
    setMessage("Give me information about Japan");
  };

  return (
    <main className="travel-app">
      {/* NAVBAR */}
      <header className="navbar">
        <div className="logo">
          <span>✈</span>
          AI Travel Concierge
        </div>

        <nav>
          <a href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#about">About</a>
        </nav>
      </header>

      {/* HERO SECTION */}
      <section className="hero" id="home">
        <div className="hero-content">
          <div className="badge">✦ AI-POWERED TRAVEL ASSISTANT</div>

          <h1>
            Your journey,
            <br />
            <span>intelligently planned.</span>
          </h1>

          <p>
            Plan smarter trips with AI-powered recommendations, live weather,
            destination information and web search.
          </p>

          <div className="quick-actions">
            <button onClick={planTokyoTrip}>
              🗼 Plan a Trip
            </button>

            <button onClick={checkParisWeather}>
              ☁ Check Weather
            </button>

            <button onClick={exploreJapan}>
              🌍 Explore Destination
            </button>
          </div>
        </div>
      </section>

      {/* CHAT SECTION */}
      <section className="chat-section">
        <div className="chat-card">
          {/* CHAT HEADER */}
          <div className="chat-header">
            <div>
              <h2>Travel Assistant</h2>

              <p>
                <span className="online-dot"></span>
                {loading ? "AI Concierge thinking..." : "AI Concierge online"}
              </p>
            </div>

            <div className="agent-icon">✈</div>
          </div>

          {/* CHAT BODY */}
          <div className="chat-body">
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-icon">🌎</div>

                <h3>Where would you like to go?</h3>

                <p>
                  Ask me about destinations, weather, attractions, countries
                  or travel planning.
                </p>
              </div>
            ) : (
              messages.map((item, index) => (
                <div
                  key={index}
                  className={`message ${
                    item.role === "user"
                      ? "user-message"
                      : "ai-message"
                  }`}
                >
                  {item.text}
                </div>
              ))
            )}

            {/* LOADING MESSAGE */}
            {loading && (
              <div className="message ai-message">
                ✈️ Planning your trip...
              </div>
            )}
          </div>

          {/* CHAT INPUT */}
          <div className="chat-input">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  sendMessage();
                }
              }}
              placeholder="Ask your travel assistant..."
              disabled={loading}
            />

            <button
              onClick={sendMessage}
              disabled={loading || !message.trim()}
            >
              {loading ? "..." : "➤"}
            </button>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="features" id="features">
        <div className="section-heading">
          <span>POWERFUL CAPABILITIES</span>

          <h2>Everything you need for smarter travel</h2>
        </div>

        <div className="feature-grid">
          {/* WEB SEARCH */}
          <div className="feature-card">
            <div>🔎</div>

            <h3>Web Search</h3>

            <p>
              Find useful and current travel information using web search.
            </p>
          </div>

          {/* WEATHER */}
          <div className="feature-card">
            <div>☁️</div>

            <h3>Live Weather</h3>

            <p>
              Get weather information for your destination before you travel.
            </p>
          </div>

          {/* COUNTRY INFORMATION */}
          <div className="feature-card">
            <div>🌍</div>

            <h3>Country Information</h3>

            <p>
              Explore country details, capitals, currencies and regions.
            </p>
          </div>

          {/* LANGGRAPH */}
          <div className="feature-card">
            <div>🧠</div>

            <h3>LangGraph Agent</h3>

            <p>
              Multi-step AI reasoning coordinates tools to answer travel
              questions.
            </p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer id="about">
        <div>
          <strong>✈ AI Travel Concierge</strong>

          <p>Intelligent travel planning powered by AI.</p>
        </div>

        <p>
          Built with Next.js • FastAPI • LangGraph • Gemini
        </p>
      </footer>
    </main>
  );
}