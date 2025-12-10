interface JsonViewerProps {
  data: unknown;
}

export default function JsonViewer({ data }: JsonViewerProps) {
  return (
    <div style={{ marginTop: "15px" }}>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
