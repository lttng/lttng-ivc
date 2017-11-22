/*
 * Copyright (c) 2017 Jonathan Rajotte-Julien <jonathan.rajotte-julien@efficios.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import java.io.IOException;
import java.io.File;
import java.util.logging.Logger;
import java.util.logging.Level;
import java.util.logging.ConsoleHandler;
import org.lttng.ust.agent.LTTngAgent;

public class App
{
    private static final int answer = 42;

    public static void main(String[] argv) throws Exception
    {
	int nrIter = Integer.parseInt(argv[0]);
	String sync_first_tp_hit_path = null;
	String sync_wait_before_last = null;

	if (argv.length > 1) {
		sync_first_tp_hit_path = argv[1];
	}
	if (argv.length > 2) {
		sync_wait_before_last = argv[2];
	}

        // Create a logger
        Logger logger = Logger.getLogger("jello");
	logger.setLevel(Level.INFO);

	LTTngAgent lttngAgent = LTTngAgent.getLTTngAgent();

	for (int i=0; i < 0 || i < nrIter; i++) {
		if ( i >= 0 && i == nrIter -1 && sync_wait_before_last != null) {
			File f = new File(sync_wait_before_last);
			while (!f.exists()) {
				Thread.sleep(1);
			}
		}
		logger.info("logging the world");
		logger.warning("some warning");
		logger.severe("error!");
		if (i == 0 && sync_first_tp_hit_path != null) {
			File f = new File(sync_first_tp_hit_path);
			f.createNewFile();
		}
	}

        // Not mandatory, but cleaner
	lttngAgent.dispose();
    }
}
