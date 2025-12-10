import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

export default function PostView() {
  const { id } = useParams();
  const [post, setPost] = useState<any>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/post/${id}`)
      .then(res => res.json())
      .then(setPost);
  }, [id]);

  if (!post) return <p>Loading...</p>;

  return (
    <div>
      <h2>{post.title}</h2>
      <p>{post.body}</p>

      <h3>Comments</h3>
      <CommentThread comments={post.comments} />
    </div>
  );
}

function CommentThread({ comments }: any) {
  if (!comments || comments.length === 0) return null;

  return (
    <ul style={{ listStyle: "none", paddingLeft: 20 }}>
      {comments.map((c: any) => (
        <li
          key={c.id}
          style={{
            marginBottom: 12,
            borderLeft: "2px solid #ddd",
            paddingLeft: 10,
          }}
        >
          <strong>{c.author}</strong>
          <p>{c.text}</p>

          {c.children && <CommentThread comments={c.children} />}
        </li>
      ))}
    </ul>
  );
}
