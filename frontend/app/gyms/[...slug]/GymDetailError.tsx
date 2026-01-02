import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface GymDetailErrorProps {
  message: string;
  onRetry: () => void;
}

export function GymDetailError({ message, onRetry }: GymDetailErrorProps) {
  return (
    <div className="flex min-h-screen flex-col px-4 py-10">
      <div className="mx-auto w-full max-w-xl">
        <Card>
          <CardHeader className="space-y-2 text-center">
            <CardTitle>ジム情報を読み込めませんでした</CardTitle>
            <CardDescription>{message}</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Button onClick={onRetry} type="button">
              再試行する
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
