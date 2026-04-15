<?php
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);
if (!$data) exit;

$msg   = $data['message'] ?? '';
$title = $data['title'] ?? 'cocare 알림';
$tags  = $data['tags'] ?? 'bell';

$ch = curl_init('https://ntfy.sh/gola-claude-alerts');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $msg,
    CURLOPT_HTTPHEADER => [
        "Title: $title",
        "Priority: high",
        "Tags: $tags",
    ],
    CURLOPT_RETURNTRANSFER => true,
]);
curl_exec($ch);
curl_close($ch);
echo 'ok';
