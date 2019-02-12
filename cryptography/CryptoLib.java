// Compilation (CryptoLibTest contains the main-method):
//   javac CryptoLibTest.java
// Running: 
//   java CryptoLibTest
import java.util.Random;
import java.math.BigInteger;
public class CryptoLib {

	/**
	 * Returns an array "result" with the values "result[0] = gcd",
	 * "result[1] = s" and "result[2] = t" such that "gcd" is the greatest
	 * common divisor of "a" and "b", and "gcd = a * s + b * t".
	 **/

	//https://brilliant.org/wiki/extended-euclidean-algorithm/
	public static int[] EEA(int a, int b) {
		// Note: as you can see in the test suite,
		// your function should work for any (positive) value of a and b.
		int gcd = 0;
		int s = 0; // x
		int t = 1; // y
		int y,u,v,q,r,m,n;
		u = 1; v = 0;
		while (a != 0) {
			q = b  / a; r = b % a;
			m = s - u * q;  n = t - v * q;
			b = a; a = r;  s = u;
			t = v; u = m; v = n;
	}
		gcd = b;
		int[] result = new int[3];
		result[0] = gcd;
		result[1] = s;
		result[2] = t;
		return result;
	}

	/**
	 * Calculates the GCD between two numbers
	 **/

	public static int gcd(int p, int q) {
	if (q == 0) return p;

	return gcd(q, p % q);
}
	/**
	 * Returns Euler's Totient for value "n".
	 **/

	public static int EulerPhi(int n) {
		if(n < 0) {
			return 0;
		}

		int res = 1;
		for(int i = 2; i < n; i++) {
			if( gcd(i,n) == 1)
				res++;
		}
		return res;
	}

	/**
	 * Returns the value "v" such that "n*v = 1 (mod m)". Returns 0 if the
	 * modular inverse does not exist.
	 **/

	//http://yourdailygeekery.com/2011/06/28/modulo-of-negative-numbers.html
	public static int ModInv(int n, int m) {
		int modbase = m;
		if(m < 0) {
			m += m;
		}
		n = (((n % m) + m) % m); // since modulo operation in java is messy we chain a second modulo to make it work when using negative numbers
		for(int i = 1; i < m; i++)
			if(((((n * i) % m) + m) % m) == 1 )
				return i;
		return 1;
	}

	// Used to calculate base ^ exponent % mod
	public static int PowerMod(int base, int exponent, int mod) {
		int res = 1;
		for(int i = 0; i < exponent; i++) {
			res *= base;
			res %= mod;
		}
		return res % mod;
	}
	
	/**
	 * Returns 0 if "n" is a Fermat Prime, otherwise it returns the lowest
	 * Fermat Witness. Tests values from 2 (inclusive) to "n/3" (exclusive).
	 **/

	public static int FermatPT(int n) {
		if ( n == 1) // special case if n is equal to 1
			return 1;
		for(int i = 2; i < n/3; i++) {
			if(PowerMod(i,n-1,n) != 1) 
				return i; // returns the witness
		}
		return 0; // if prime return 0
	}

	/**
	 * Returns the probability that calling a perfect hash function with
	 * "n_samples" (uniformly distributed) will give one collision (i.e. that
	 * two samples result in the same hash) -- where "size" is the number of
	 * different output values the hash function can produce.
	 **/
	public static double powFunc(double base, double exp) {
		double result = 1;
		for(int i = 0; i < base; i++) {
			result *= base;
		}
		return result;
	}
	public static double logFunc(double x) {
		return (x > 1) ? 1 + logFunc(x / 2) : 0;
	}

	public static double log1pFunc(double x) {
		if ( x <= Math.abs(1))
			return 0;
		else
			return logFunc(x + 1);
	}
	//n_samples shares the same birhtday = 24
	//size number of days = 356
	//https://medium.com/i-math/the-birthday-problem-307f31a9ac6f
	public static double HashCP(double n_samples, double size) {
		double probability = 1;
		for(double i = 0; i < n_samples; i++) { //
			probability = probability * (i - size) / size; // ex 356!/356...
		}
		return 1-probability;
	}

}
