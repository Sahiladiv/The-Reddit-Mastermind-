import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./SubredditPosts.css";

export default function SubredditPosts() {
  const { subreddit } = useParams();
  const navigate = useNavigate();
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    fetch(`http://localhost:8000/subreddit/${subreddit}/posts`)
      .then((res) => res.json())
      .then(setPosts);
  }, [subreddit]);

  return (
    <div className="posts-page">
      <div className="header-row">
        <button className="home-btn" onClick={() => navigate("/")}>
          ⟵ Home
        </button>
        <h1 className="subreddit-title">r/{subreddit}</h1>
      </div>

      <div className="post-list">
        {posts.map((p: any) => (
          <div
            key={p.id}
            className="post-card"
            onClick={() => navigate(`/post/${p.id}`)}
          >
            <h3>{p.title}</h3>
            <p>{p.body.slice(0, 150)}...</p>
          </div>
        ))}
      </div>
    </div>
  );
}
