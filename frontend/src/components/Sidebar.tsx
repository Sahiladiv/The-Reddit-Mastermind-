import React, { useEffect, useState } from "react";
import "./Sidebar.css";

export default function Sidebar() {
  const [subreddits, setSubreddits] = useState([]);

  useEffect(() => {
    fetch("https://the-reddit-mastermind.onrender.com/subreddits")
      .then(res => res.json())
      .then(setSubreddits);
  }, []);

  return (
    <div className="sidebar">
      <h2 className="sidebar-title">Subreddits</h2>

      <ul className="subreddit-list">
        {subreddits.map((s: any) => (
          <li
            key={s.id}
            className="subreddit-item"
            onClick={() => (window.location.href = `/r/${s.name}`)}
          >
            r/{s.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
