export default function CartPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-600 px-4 py-3 flex items-center">
        <a href="/" className="text-white mr-3">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </a>
        <h1 className="text-lg font-bold text-white">Корзина</h1>
      </header>
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center text-gray-400">
          <p className="text-lg">Корзина пуста</p>
          <a href="/" className="text-blue-600 text-sm mt-2 inline-block">
            Перейти в каталог
          </a>
        </div>
      </main>
    </div>
  );
}
