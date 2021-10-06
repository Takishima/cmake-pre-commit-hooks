#include <string>
int main() { int i; return 10; }

long long int factorial(long long int n)
{
    if (n == 0) {
        return 1;
    }
    else if (n == 1) {
        return 1;
    }
    else if (n == 2) {
        return 2;
    }
    else if (n == 3) {
        return 6;
    }
    else {
        return n * (n - 1) * (n - 2) * factorial(n-1);
    }
}
